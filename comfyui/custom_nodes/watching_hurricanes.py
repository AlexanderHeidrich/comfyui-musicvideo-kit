"""Three nodes for driving MiniMax H3 from a MusicVideoKit song folder.

Copy this file into ComfyUI/custom_nodes/ and restart ComfyUI. Stdlib only -
no torch, no numpy, nothing to install.

  HurricaneSongFolder         point it at songs/<name> and it batches the whole song:
                       prompt, slice, frame count and reference sheets per scene
  HurricaneBuildSong          runs ./mvkit on the host first, then the same thing
  HurricaneClipFolder  walks a folder of rendered clips, for the upscale pass
  HurricaneStoryboardScene    reads ALL_scenes.txt, picks one scene, hands out its
                       blocks and its timing
  HurricaneReferenceInventory works out the live <Picture n>/<Video n>/<Audio n> tags
                       from what is actually connected
  HurricanePromptBuilder      assembles the six sections; optionally via a local LLM

Everything above the ComfyUI section is plain python and can be imported and
tested without ComfyUI present.
"""

import json
import os
import re
import urllib.error
import urllib.request

CATEGORY = "Watching Hurricanes"

FPS = 24
GRID = [f for f in range(124, 363) if f % 17 == 5]
SECTIONS = ("subject_definitions", "summary", "retention_analysis",
            "detailed_description", "overall_soundscape", "non_diegetic_music")


# --------------------------------------------------------------------------
# the DSL, and the frame grid
# --------------------------------------------------------------------------

def snap_frames(seconds):
    """H3 accepts only frames % 17 == 5 in 124..362 and rounds UP, so pick the
    first grid value that covers `seconds` rather than the nearest one."""
    # the DSL carries mm:ss.sss, so a duration that IS a grid value arrives up to
    # half a millisecond off. Absorb that: grid steps are 17 frames apart, so a
    # quarter-frame of slack cannot reach the next one.
    want = seconds * FPS - 0.25
    for f in GRID:
        if f >= want:
            return f
    return GRID[-1]


def parse_time(tok):
    """mm:ss.sss or plain seconds -> float"""
    tok = tok.strip()
    if ":" in tok:
        m, s = tok.rsplit(":", 1)
        return int(m) * 60 + float(s)
    return float(tok)


def parse_dsl(text):
    """-> {"bible":..., "style":..., "tail":..., "scenes":[...]}

    Directives sit alone at the start of a line; '#' is a comment. @SCENE takes
    `start-end | title` in absolute song time.
    """
    out = {"bible": [], "style": [], "tail": [], "scenes": []}
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.lstrip().startswith("#"):
            continue
        head = line.strip()
        if head.startswith("@SCENE"):
            body = head[len("@SCENE"):].strip()
            rng, _, title = body.partition("|")
            a, _, b = rng.strip().partition("-")
            # mm:ss.sss holds a colon, so split on the '-' between the two stamps
            if not b:
                a, b = rng.strip(), rng.strip()
            sc = {"title": title.strip() or "scene %d" % (len(out["scenes"]) + 1),
                  "start": parse_time(a), "end": parse_time(b), "action": []}
            out["scenes"].append(sc)
            cur = sc["action"]
            continue
        for key in ("BIBLE", "STYLE", "TAIL"):
            if head == "@" + key:
                cur = out[key.lower()]
                break
        else:
            if cur is not None:
                cur.append(line)
            continue
    for k in ("bible", "style", "tail"):
        out[k] = "\n".join(out[k]).strip()
    for sc in out["scenes"]:
        sc["action"] = "\n".join(sc["action"]).strip()
        sc["duration"] = max(0.0, sc["end"] - sc["start"])
        sc["frames"] = snap_frames(sc["duration"]) if sc["duration"] else GRID[0]
    return out


def pick_scene(parsed, index):
    """1-based, clamped - a batch counter that runs past the end should not kill
    the whole queue run."""
    scenes = parsed["scenes"]
    if not scenes:
        raise ValueError("no @SCENE blocks in the DSL file")
    i = min(max(int(index), 1), len(scenes)) - 1
    return scenes[i]


# --------------------------------------------------------------------------
# reference tags, in H3's own order
# --------------------------------------------------------------------------

def reference_tags(pictures, videos, standalone_audio, video_audio_flags=None):
    """H3 skips unconnected slots and numbers the survivors 1..n per type. A
    reference video's own soundtrack claims an <Audio> number BEFORE any
    standalone audio, so the two cannot be numbered independently.

    pictures / videos / standalone_audio: lists of labels for CONNECTED slots.
    video_audio_flags: per connected video, whether it carries its own audio.
    -> list of (tag, kind, label)
    """
    flags = list(video_audio_flags or [])
    flags += [False] * (len(videos) - len(flags))
    out = []
    for i, label in enumerate(pictures, 1):
        out.append(("<Picture %d>" % i, "picture", label))
    for i, label in enumerate(videos, 1):
        out.append(("<Video %d>" % i, "video", label))
    n = 0
    for i, label in enumerate(videos):
        if flags[i]:
            n += 1
            out.append(("<Audio %d>" % n, "audio", "soundtrack of <Video %d>" % (i + 1)))
    for label in standalone_audio:
        n += 1
        out.append(("<Audio %d>" % n, "audio", label))
    return out


def inventory_text(tags, limits=True):
    lines = ["%-12s %s" % (t, label) for t, _, label in tags]
    if limits:
        pics = sum(1 for _, k, _ in tags if k == "picture")
        vids = sum(1 for _, k, _ in tags if k == "video")
        auds = sum(1 for _, k, _ in tags if k == "audio")
        media = pics + vids + auds
        lines.append("")
        lines.append("media inputs : %d of 12  (%d image, %d video, %d audio)"
                     % (media, pics, vids, auds))
        for bad in ([] if pics <= 9 else ["more than 9 reference images"]) + \
                   ([] if vids <= 3 else ["more than 3 reference videos"]) + \
                   ([] if auds <= 3 else ["more than 3 audio references"]) + \
                   ([] if media <= 12 else ["more than 12 media inputs in total"]) + \
                   ([] if pics or vids else ["audio alone is not a valid input - "
                                             "connect at least one image or video"]):
            lines.append("! " + bad)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# a whole song folder, read straight off disk
# --------------------------------------------------------------------------

def read_song_folder(song):
    """-> {"scenes": [...], "refs": [...], "inventory": str}

    __SCENES.tsv is the authority on pairing: it already says which prompt files
    and which slice belong to each scene, so nothing here re-derives it.
    """
    man = os.path.join(song, "__SCENES.tsv")
    if not os.path.isfile(man):
        raise FileNotFoundError(
            "%s has no __SCENES.tsv - point song_path at a built song folder "
            "(the one holding NN_*.txt), not at _source or the repo root." % song)
    with open(man, encoding="utf-8") as fh:
        rows = [l.rstrip("\n").split("\t") for l in fh if l.strip()]
    head, rows = rows[0], rows[1:]
    scenes = []
    for r in rows:
        d = dict(zip(head, r))
        audio = (d.get("audio") or "-").strip()
        pf_all = [f for f in (d.get("prompts") or "").split() if f.endswith(".txt")]
        # the real title is the slug in the filename; the lyrics column is a lyric
        slug_t = re.sub(r"^\d+_|-v\d+\.txt$", "", pf_all[0]).replace("-", " ") \
            if pf_all else ""
        scenes.append({
            "scene": d.get("scene", "?"),
            "title": slug_t,
            "lyrics": (d.get("lyrics") or "").strip(),
            "frames": int(d.get("frames") or 0),
            "audio": "" if audio in ("", "-") else os.path.join(song, audio),
            "prompts": {f.rsplit("-", 1)[-1][:-4]: os.path.join(song, f)
                        for f in (d.get("prompts") or "").split() if f.endswith(".txt")},
        })
    refs, inventory = [], ""
    rj = os.path.join(song, "_source", "refs.json")
    if os.path.isfile(rj):
        with open(rj, encoding="utf-8") as fh:
            data = json.load(fh)
        rdir = os.path.join(song, "_source", "refs")
        for item in data.get("images", []):
            refs.append({"tag": item.get("tag", ""), "slug": item.get("slug", ""),
                         "kind": item.get("kind", ""),
                         "path": os.path.join(rdir, item.get("file", ""))})
        inventory = "\n".join("%-12s %s (%s)" % (i["tag"], i["slug"], i["kind"])
                              for i in refs)
        tag = data.get("scene_audio_tag")
        if tag:
            inventory += "\n%-12s this scene's slice of the song" % tag
    return {"scenes": scenes, "refs": refs, "inventory": inventory}


# --------------------------------------------------------------------------
# a folder of rendered clips, for the upscale pass
# --------------------------------------------------------------------------

VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv", ".avi")


def list_clips(folder, extensions=""):
    """-> sorted [(path, stem)] so the queue walks the folder in a fixed order.

    Sorted by name, which is why the render prefix names clips after their
    prompt: NN_slug-vN sorts into scene order on its own.
    """
    if not folder or not os.path.isdir(folder):
        raise FileNotFoundError("source_dir is not a folder: %r" % folder)
    exts = tuple("." + e.strip().lstrip(".").lower()
                 for e in extensions.split(",") if e.strip()) or VIDEO_EXT
    out = []
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(exts) and not f.startswith("."):
            out.append((os.path.join(folder, f), os.path.splitext(f)[0]))
    if not out:
        raise FileNotFoundError("no %s in %s" % ("/".join(exts), folder))
    return out


# --------------------------------------------------------------------------
# the six sections
# --------------------------------------------------------------------------

def indent(text, pad="  "):
    return "\n".join(pad + l if l.strip() else "" for l in text.splitlines())


def build_prompt(bible, style, action, soundscape, music, inventory, retention,
                 task="[reference generation + audio reuse]"):
    """A valid six-section H3 prompt, in the official order. The style belongs
    before [Shot 1] inside detailed_description, not in retention_analysis -
    that section is a reference ledger, not a look brief."""
    subject = bible if not inventory else \
        "References supplied with this generation:\n" + indent(inventory) + \
        ("\n\n" + bible if bible else "")
    first = (action.strip().splitlines() or [""])[0]
    summary = "%s %s" % (task, first.strip())
    detailed = (style + "\n\n" + action).strip() if style else action.strip()
    body = [
        ("subject_definitions", subject),
        ("summary", summary),
        ("retention_analysis", retention or "no references supplied."),
        ("detailed_description", detailed),
        ("overall_soundscape", soundscape),
        ("non_diegetic_music", music),
    ]
    return "\n\n".join("%s\n%s" % (k, indent(v)) for k, v in body if v.strip()) + "\n"


def llm_rewrite(host, model, prompt, system, timeout=120):
    """One OpenAI-compatible /chat/completions call - LM Studio, Ollama, whatever
    speaks it. Returns None on any failure so the caller can fall back."""
    url = host.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/v1/chat/completions" if "/v1" not in url else "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "temperature": 0.4, "stream": False,
    }).encode()
    req = urllib.request.Request(url, data=body,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            got = json.load(resp)
        return got["choices"][0]["message"]["content"]
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError,
            IndexError, ValueError, TimeoutError):
        return None


# --------------------------------------------------------------------------
# ComfyUI nodes
# --------------------------------------------------------------------------

class HurricaneStoryboardScene:
    """Reads ALL_scenes.txt and hands out one scene: its blocks and its timing.

    Set scene_index to `increment` and the queue's batch count to the number of
    scenes to walk the whole song. `frames` is already on H3's grid.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING",
                    "INT", "FLOAT", "FLOAT", "FLOAT", "INT")
    RETURN_NAMES = ("bible", "style", "action", "tail", "title",
                    "frames", "start", "end", "duration", "scene_count")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "dsl_path": ("STRING", {"default": "", "multiline": False}),
            "scene_index": ("INT", {"default": 1, "min": 1, "max": 9999}),
        }}

    @classmethod
    def IS_CHANGED(cls, dsl_path, scene_index):
        try:
            return "%s:%s:%s" % (dsl_path, os.path.getmtime(dsl_path), scene_index)
        except OSError:
            return "%s:missing:%s" % (dsl_path, scene_index)

    def run(self, dsl_path, scene_index):
        if not dsl_path or not os.path.isfile(dsl_path):
            raise FileNotFoundError(
                "dsl_path does not point at a file: %r. It wants the "
                "ALL_scenes.txt inside a song folder." % dsl_path)
        with open(dsl_path, encoding="utf-8") as fh:
            parsed = parse_dsl(fh.read())
        sc = pick_scene(parsed, scene_index)
        return (parsed["bible"], parsed["style"], sc["action"], parsed["tail"],
                sc["title"], int(sc["frames"]), float(sc["start"]),
                float(sc["end"]), float(sc["duration"]), len(parsed["scenes"]))


class HurricaneReferenceInventory:
    """The live <Picture n>/<Video n>/<Audio n> tags for what is connected.

    H3 renumbers over the slots it actually receives, so a gap shifts every tag
    after it. Leave a slot empty here and the numbering closes up the same way,
    which is the point: read the tags off this node instead of hardcoding them.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("inventory", "media_count")

    @classmethod
    def INPUT_TYPES(cls):
        opt = {}
        for i in range(1, 10):
            opt["picture_%d" % i] = ("IMAGE",)
            opt["picture_%d_label" % i] = ("STRING", {"default": ""})
        for i in range(1, 4):
            opt["video_%d" % i] = ("IMAGE",)
            opt["video_%d_label" % i] = ("STRING", {"default": ""})
            opt["video_%d_has_audio" % i] = ("BOOLEAN", {"default": False})
        for i in range(1, 4):
            opt["audio_%d" % i] = ("AUDIO",)
            opt["audio_%d_label" % i] = ("STRING", {"default": ""})
        return {"required": {}, "optional": opt}

    def run(self, **kw):
        def connected(prefix, n):
            got, labels = [], []
            for i in range(1, n + 1):
                if kw.get("%s_%d" % (prefix, i)) is not None:
                    got.append(i)
                    labels.append(kw.get("%s_%d_label" % (prefix, i)) or
                                  "%s %d" % (prefix, i))
            return got, labels

        _, pics = connected("picture", 9)
        vids_i, vids = connected("video", 3)
        _, auds = connected("audio", 3)
        flags = [bool(kw.get("video_%d_has_audio" % i)) for i in vids_i]
        tags = reference_tags(pics, vids, auds, flags)
        return (inventory_text(tags), len(tags))


class HurricanePromptBuilder:
    """Assembles the six sections H3 expects, in order.

    With use_llm off it is a deterministic template and always produces a valid
    prompt. With it on, a local OpenAI-compatible endpoint gets one pass at the
    prose; if that call fails for any reason the template result is returned
    instead, so a dead LLM never empties the queue.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "note")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bible": ("STRING", {"default": "", "multiline": True}),
                "style": ("STRING", {"default": "", "multiline": True}),
                "action": ("STRING", {"default": "", "multiline": True}),
                "overall_soundscape": ("STRING", {"default": "", "multiline": True}),
                "non_diegetic_music": ("STRING", {"default": "", "multiline": True}),
                "use_llm": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "inventory": ("STRING", {"default": "", "multiline": True}),
                "retention_analysis": ("STRING", {"default": "", "multiline": True}),
                "task_type": ("STRING", {"default": "[reference generation + audio reuse]"}),
                "llm_host": ("STRING", {"default": "http://127.0.0.1:1234"}),
                "llm_model": ("STRING", {"default": "local-model"}),
            },
        }

    def run(self, bible, style, action, overall_soundscape, non_diegetic_music,
            use_llm, inventory="", retention_analysis="",
            task_type="[reference generation + audio reuse]",
            llm_host="http://127.0.0.1:1234", llm_model="local-model"):
        base = build_prompt(bible, style, action, overall_soundscape,
                            non_diegetic_music, inventory, retention_analysis,
                            task_type)
        if not use_llm:
            return (base, "template")
        system = (
            "You tighten prompts for the MiniMax H3 reference-to-video model. "
            "Keep the six section headings exactly as given and in the same "
            "order: " + ", ".join(SECTIONS) + ". Keep every reference tag such "
            "as <Picture 2> byte for byte. Keep quoted dialogue and lyrics "
            "verbatim in their original language. Write all description in "
            "English, in concrete physical detail; never use words like "
            "cinematic or epic. Do not invent references, shots or sound. "
            "Return the prompt only."
        )
        got = llm_rewrite(llm_host, llm_model, base, system)
        if not got:
            return (base, "llm unreachable or refused - template used")
        missing = [s for s in SECTIONS if s not in got]
        if missing:
            return (base, "llm dropped %s - template used" % ", ".join(missing))
        return (got, "llm: %s" % llm_model)


class HurricaneSongFolder:
    """Point this at a song folder and it batches the whole song.

    Set scene_index to `increment` and the queue's batch count to scene_count,
    and every scene comes out in turn: its finished prompt, its slice of the
    song, its frame count and the reference sheets. Nothing to re-type per scene
    and no __batch/ lists needed.

    Paths come out as strings on purpose - loading an image or an audio file into
    ComfyUI's own types needs torch, and this file is deliberately stdlib only.
    Wire audio_path into a Load Audio (Path), and ref_1..ref_9 into image loaders
    that take a path. Empty strings mean that slot is simply not used.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING", "INT", "STRING",
                    "STRING", "STRING", "STRING", "STRING", "STRING", "STRING",
                    "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "audio_path", "frames", "title", "scene_count",
                    "inventory", "ref_1", "ref_2", "ref_3", "ref_4", "ref_5",
                    "ref_6", "ref_7", "ref_8", "ref_9", "save_prefix")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "song_path": ("STRING", {"default": "", "multiline": False}),
            "scene_index": ("INT", {"default": 1, "min": 1, "max": 9999}),
            "variant": (["v1", "v2", "v3"], {"default": "v1"}),
            "out_subfolder": ("STRING", {"default": "", "multiline": False}),
        }}

    @classmethod
    def IS_CHANGED(cls, song_path, scene_index, variant, out_subfolder=""):
        try:
            m = os.path.getmtime(os.path.join(song_path, "__SCENES.tsv"))
        except OSError:
            m = "missing"
        return "%s:%s:%s:%s:%s" % (song_path, m, scene_index, variant, out_subfolder)

    def run(self, song_path, scene_index, variant, out_subfolder=""):
        data = read_song_folder(song_path)
        scenes = data["scenes"]
        if not scenes:
            raise ValueError("__SCENES.tsv lists no scenes")
        sc = scenes[min(max(int(scene_index), 1), len(scenes)) - 1]
        pf = sc["prompts"].get(variant)
        if not pf:
            have = ", ".join(sorted(sc["prompts"])) or "none"
            raise ValueError("scene %s has no %s variant (it has: %s)"
                             % (sc["scene"], variant, have))
        with open(pf, encoding="utf-8") as fh:
            prompt = fh.read()
        paths = [r["path"] for r in data["refs"]][:9]
        paths += [""] * (9 - len(paths))
        # save_prefix groups the renders per song and names each after its prompt,
        # so the clips come out of ComfyUI already sorted and already paired
        base = (out_subfolder.strip().strip("/") or
                os.path.basename(os.path.abspath(song_path)))
        stem = os.path.basename(pf)[:-4]                  # NN_slug-vN
        prefix = "%s/%s" % (base, stem)
        return (prompt, sc["audio"], sc["frames"],
                "%s %s" % (sc["scene"], sc["title"]), len(scenes),
                data["inventory"]) + tuple(paths) + (prefix,)


class HurricaneBuildSong:
    """Runs the kit's own pipeline on the host, then behaves like HurricaneSongFolder.

    This is the "hand it a pdf and an mp3" route. It shells out to ./mvkit, so
    ffmpeg and whisper stay outside ComfyUI where they belong - nothing here
    decodes audio or reads a pdf itself.

    It is a convenience, not the recommended path. Preparing a song is slow,
    interactive work (the screenplay wants reading, the style wants deciding) and
    doing it inside a render queue hides that. Run `mvkit all` in a terminal and
    point HurricaneSongFolder at the result unless you specifically want one button.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING", "INT", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "audio_path", "frames", "title", "scene_count",
                    "save_prefix", "log")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "kit_path": ("STRING", {"default": "", "multiline": False}),
            "song_name": ("STRING", {"default": "", "multiline": False}),
            "scene_index": ("INT", {"default": 1, "min": 1, "max": 9999}),
            "variant": (["v1", "v2", "v3"], {"default": "v1"}),
            "stage": (["build only", "split + build", "everything"],
                      {"default": "build only"}),
        }}

    @classmethod
    def IS_CHANGED(cls, kit_path, song_name, scene_index, variant, stage):
        # `everything` re-transcribes and re-splits, so never cache it
        return float("nan") if stage == "everything" else \
            "%s:%s:%s:%s:%s" % (kit_path, song_name, scene_index, variant, stage)

    def run(self, kit_path, song_name, scene_index, variant, stage):
        import subprocess
        kit = os.path.abspath(kit_path or ".")
        mvkit = os.path.join(kit, "mvkit")
        if not os.path.isfile(mvkit):
            raise FileNotFoundError(
                "no ./mvkit in %s - kit_path must be the checkout of the kit, the "
                "folder holding mvkit and bin/" % kit)
        steps = {"build only": ["build"],
                 "split + build": ["split", "build"],
                 "everything": ["all"]}[stage]
        log = []
        for step in steps:
            r = subprocess.run(["bash", mvkit, step, song_name], cwd=kit,
                               capture_output=True, text=True)
            log.append("$ mvkit %s %s\n%s%s" % (step, song_name, r.stdout, r.stderr))
            if r.returncode != 0:
                raise RuntimeError("mvkit %s failed:\n%s" % (step, r.stderr[-2000:]))
        song = os.path.join(kit, "songs", song_name)
        out = HurricaneSongFolder().run(song, scene_index, variant)
        return (out[0], out[1], out[2], out[3], out[4], out[15], "\n".join(log))


class HurricaneClipFolder:
    """Walks a folder of rendered clips, one per queue run - the upscale pass.

    Nothing to do with H3: this is the step after it. Point source_dir at the
    folder the renders landed in, set clip_index to `increment` and the batch
    count to clip_count, and every clip comes through in name order.

    out_prefix keeps each clip's own name, so an upscaled file stays paired with
    the prompt that made it. ComfyUI will not write outside its own output
    folder, so out_subfolder is a path INSIDE ComfyUI/output - that is its path
    sanitising, not a choice made here.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("video_path", "out_prefix", "clip_count", "name")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "source_dir": ("STRING", {"default": "", "multiline": False}),
            "clip_index": ("INT", {"default": 1, "min": 1, "max": 99999}),
            "out_subfolder": ("STRING", {"default": "upscaled"}),
            "extensions": ("STRING", {"default": "mp4,mov,webm,mkv"}),
        }}

    @classmethod
    def IS_CHANGED(cls, source_dir, clip_index, out_subfolder, extensions):
        try:
            m = os.path.getmtime(source_dir)
        except OSError:
            m = "missing"
        return "%s:%s:%s:%s:%s" % (source_dir, m, clip_index, out_subfolder,
                                   extensions)

    def run(self, source_dir, clip_index, out_subfolder, extensions):
        clips = list_clips(source_dir, extensions)
        # deliberately NOT clamped: an unattended run with the batch count set too
        # high would otherwise re-render the last clip over and over all night
        if int(clip_index) > len(clips):
            raise ValueError(
                "clip_index %d but the folder holds %d clip(s). Set the queue's "
                "batch count to clip_count (%d), not higher."
                % (int(clip_index), len(clips), len(clips)))
        path, stem = clips[max(int(clip_index), 1) - 1]
        sub = out_subfolder.strip().strip("/")
        return (path, "%s/%s" % (sub, stem) if sub else stem, len(clips), stem)


NODE_CLASS_MAPPINGS = {
    "HurricaneSongFolder": HurricaneSongFolder,
    "HurricaneBuildSong": HurricaneBuildSong,
    "HurricaneClipFolder": HurricaneClipFolder,
    "HurricaneStoryboardScene": HurricaneStoryboardScene,
    "HurricaneReferenceInventory": HurricaneReferenceInventory,
    "HurricanePromptBuilder": HurricanePromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HurricaneSongFolder": "Hurricane Song Folder",
    "HurricaneBuildSong": "Hurricane Build Song",
    "HurricaneClipFolder": "Hurricane Clip Folder (upscale pass)",
    "HurricaneStoryboardScene": "Hurricane Storyboard Scene",
    "HurricaneReferenceInventory": "Hurricane Reference Inventory",
    "HurricanePromptBuilder": "Hurricane Prompt Builder",
}

# the nodes were called MV* before the rename. Keep the old class names working so
# a workflow saved against them still loads.
for _old, _new in (("MVSongFolder", "HurricaneSongFolder"),
                   ("MVBuildSong", "HurricaneBuildSong"),
                   ("MVStoryboardScene", "HurricaneStoryboardScene"),
                   ("MVReferenceInventory", "HurricaneReferenceInventory"),
                   ("MVPromptBuilder", "HurricanePromptBuilder")):
    NODE_CLASS_MAPPINGS[_old] = NODE_CLASS_MAPPINGS[_new]

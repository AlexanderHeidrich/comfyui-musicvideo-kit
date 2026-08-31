#!/usr/bin/env python3
"""Assemble per-scene H3 prompts from the shared blocks plus per-scene content.

  build_storyboards.py <song-dir>

Reads   <song>/_source/scenes.tsv     timing spine (bin/make_scenes.py)
        <song>/_source/bible.txt      cast, world, rules
        <song>/_source/style.txt      the look
        <song>/_source/tail.txt       sound
        <song>/_source/content.json   {"<scene>": {title, lyrics, shot1, shot2}}
        <song>/_source/refs.json      live H3 tags (bin/scan_refs.py)
Writes  <song>/NN_slug-v{1,2,3}.txt   paste-ready prompts, H3's six sections, no
                                      markup - beside the NN_slug.mp3 they share
        <song>/__SCENES.tsv           frames, timing and pairing for every scene
        <song>/ALL_scenes.txt         the storyboard DSL, for the ComfyUI node
        <song>/__READ_ME.txt          what the folder is

Edit _source/* and re-run; nothing is duplicated by hand.
"""
import csv, json, os, re, shutil, sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CAM_FALLBACK = """[v1] wide master
Locked off, wide, no camera move. The full setting with the character placed in
it, deep enough focus that the whole location reads at once.

[v2] alternative angle, medium
Locked off medium on a different axis - roughly ninety degrees off the master,
lower and closer. Same moment, seen from the other side of it.

[v3] close / detail
Locked off close on the single most specific thing in the action - a face, a
hand, a point of contact. Everything else reads as soft painted colour."""

MUSIC_DEFAULT = ("The supplied song excerpt is the only music. Do not add, invent or\n"
                 "extend any instrumentation - no score, no stings, no risers.")


# H3 takes camera motion as natural English - motion type, then amplitude, then
# speed (MiniMax's own prompt guide, section 4.3). The bracket tokens are Hailuo
# 02's grammar and H3 ignores them, so they stay this kit's authoring shorthand
# and are translated here.
CAM_MOVES = {
    "zoom in": "zooms in", "zoom out": "zooms out",
    "push in": "pushes in", "pull out": "pulls out",
    "pan left": "pans left", "pan right": "pans right",
    "truck left": "trucks left", "truck right": "trucks right",
    "tilt up": "tilts up", "tilt down": "tilts down",
    "pedestal up": "pedestals up", "pedestal down": "pedestals down",
    "arc shot": "arcs around the subject",
    "tracking shot": "tracks the subject, holding the framing",
    "static shot": "holds a static shot",
    "shake": "shakes slightly", "shake slightly": "shakes slightly",
    "shake strongly": "shakes strongly",
    "roll clockwise": "rolls clockwise",
    "roll counterclockwise": "rolls counterclockwise",
    "pov": "stays in the subject's point of view",
}
CAM_HEAD = re.compile(r"^\s*\[([^\]]+)\]\s*")


def camera_sentence(block, bad=None):
    """[Zoom in, slow, large] Framing.  ->  Framing. The camera zooms in with
    large amplitude at slow speed."""
    m = CAM_HEAD.match(block)
    if not m:
        return block.strip()
    moves, amp, speed = [], "", ""
    for tok in (t.strip().lower() for t in m.group(1).split(",")):
        if not tok:
            continue
        if tok in ("slow", "fast"):
            speed = " at %s speed" % tok
        elif tok in ("small", "large"):
            amp = " with %s amplitude" % tok
        elif tok in CAM_MOVES:
            moves.append(CAM_MOVES[tok])
        elif bad is not None:
            bad.add(tok)
    rest = block[m.end():].strip()
    if not moves:
        return rest
    if "static" in m.group(1).lower():
        amp = speed = ""
    verb = moves[0] if len(moves) == 1 else "%s and %s" % (", ".join(moves[:-1]), moves[-1])
    sentence = "The camera %s%s%s." % (verb, amp, speed)
    return (rest + " " + sentence).strip() if rest else sentence


def strip_comments(text):
    return "\n".join(l for l in text.splitlines()
                     if not l.lstrip().startswith("#")).strip()


def config(src, name):
    """a song's own copy of a config file wins over the shared template"""
    for path in (os.path.join(src, name), os.path.join(KIT, "templates", name)):
        if os.path.isfile(path):
            return strip_comments(open(path, encoding="utf-8").read())
    return None


def read_cameras(src):
    """-> {tag: (label, block)} from cameras.txt"""
    text = config(src, "cameras.txt") or CAM_FALLBACK
    cams, tag, label, body = {}, None, None, []
    for line in text.splitlines():
        m = re.match(r"^\[(v\d+)\]\s*(.*)$", line.strip())
        if m:
            if tag:
                cams[tag] = (label, "\n".join(body).strip())
            tag, label, body = m.group(1), m.group(2).strip() or m.group(1), []
        elif tag:
            body.append(line)
    if tag:
        cams[tag] = (label, "\n".join(body).strip())
    if not cams:
        sys.exit("cameras.txt has no [vN] blocks")
    return cams


def wrap(text, width):
    out, line = [], ""
    for w in text.split():
        if line and len(line) + 1 + len(w) > width:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def read_refs(song):
    path = os.path.join(song, "_source", "refs.json")
    if not os.path.isfile(path):
        return None
    return json.load(open(path, encoding="utf-8"))


def ref_lines(refs):
    if not refs:
        return ["<Picture 1>  the character reference",
                "<Audio 1>    this window of the song"]
    out = ["%-12s %s (%s)" % (i["tag"], i["slug"], i["kind"])
           for i in refs.get("images", []) + refs.get("videos", [])]
    tag = refs.get("scene_audio_tag", "<Audio 1>") if "scene_audio_tag" in refs \
        else "<Audio 1>"
    if tag:
        out.append("%-12s this window of the song" % tag)
    return out


RETENTION = {
    "char": ("partially_preserved", "the design, proportions, colour model and "
             "every marking are preserved exactly and never drift between scenes; "
             "only the sheet's plain backdrop and the cast shadow under the figure "
             "are dropped. How the character is rendered is set by the style below."),
    "prop": ("partially_preserved", "the shape, material and colour of the object "
             "are preserved; the reference's own rendering and backdrop are not."),
    "style": ("attribute_transfer", "the palette, the line weight and the way "
              "shading is laid down are transferred to everything drawn in this "
              "shot. The board itself is never a thing in the scene and is never "
              "drawn."),
    "loc": ("partially_preserved", "a background painting. Where this shot is set "
            "in that place its architecture, layout and palette are preserved and "
            "nothing in it is a subject; where the shot is set elsewhere it "
            "contributes nothing."),
    "video": ("weak_reference", "only its camera movement, cutting and rhythm are "
              "referenced."),
}

# H3 draws what the ledger tells it to preserve, so a character that is not in
# this shot needs its own line saying so - otherwise every reference turns up in
# every scene, or bleeds its features onto whoever is there.
ABSENT = {
    "char": ("weak_reference", "this character is NOT in this shot. Do not draw "
             "it anywhere in frame, at any size, and do not let any of its "
             "features reach another character. It is supplied only so its "
             "design stays fixed for the scenes it is in."),
    "prop": ("weak_reference", "this object is NOT in this shot and is not drawn."),
}

ARTICLES = {"der", "die", "das", "the", "a", "an"}


def read_aliases(src):
    """`_source/refs/__ALIASES.txt`: `<slug>: word, word` - the words that mean a
    reference is in a shot. The slugs are whatever language the files are named
    in; the shot descriptions are English, so they rarely match on their own."""
    path = os.path.join(src, "refs", "__ALIASES.txt")
    out = {}
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if ":" not in line:
                continue
            slug, terms = line.split(":", 1)
            out[slug.strip().lower()] = [t.strip().lower()
                                         for t in terms.split(",") if t.strip()]
    return out


def terms_for(item, aliases):
    words = [w for w in item["slug"].lower().split() if w not in ARTICLES]
    return aliases.get(item["slug"].lower(), words)


def present_tags(refs, text, aliases, declared=None):
    """which references the shot actually names. A scene may override the whole
    guess with a "cast" list of slugs - scene 20 draws a frog on a page and must
    not put a frog by the pond."""
    low = text.lower()
    out = set()
    for i in (refs or {}).get("images", []) + (refs or {}).get("videos", []):
        if declared is not None and i["kind"] in ABSENT:
            if i["slug"].lower() in declared:
                out.add(i["tag"])
            continue
        terms = terms_for(i, aliases)
        # "-hen house" blanks the phrase first, so "hen" no longer matches inside it
        hay = low
        for t in terms:
            if t.startswith("-"):
                hay = re.sub(word_pattern(t[1:]), " ", hay)
        for t in terms:
            if not t.startswith("-") and re.search(word_pattern(t), hay):
                out.add(i["tag"])
                break
    return out


def word_pattern(term):
    """whole-word match, but a term may end in punctuation - "the frog sings the
    line." is the off-screen vocal credit and must not count as presence."""
    left = r"\b" if term[:1].isalnum() else ""
    right = r"\b" if term[-1:].isalnum() else ""
    return left + re.escape(term) + right


# The short build. Every published H3 guide puts the prompt limit at 7,000
# characters and a full one here is four times that, so v4 is the same shot said
# briefly: only the subjects in the scene, bound the way the guide binds them.
SHORT = {
    "char": "partially_preserved - design, proportions and colour model exactly.",
    "prop": "partially_preserved - shape, material and colour.",
    "style": "attribute_transfer - palette, line weight and shading only. Never drawn.",
    "loc": "partially_preserved - the layout, architecture and palette of that place.",
    "video": "weak_reference - movement and rhythm only.",
}
SHORT_ABSENT = "weak_reference - NOT in this shot. Do not draw it and do not let its features reach anything else."


def read_brief(src):
    """`_source/brief.txt` - the short forms v4 is assembled from. Blocks are
    `[style] [sound] [music]` and one `[subject <ref slug>]` per character, where
    {S} and {P} are replaced by that scene's live <Subject n> / <Picture n>."""
    path = os.path.join(src, "brief.txt")
    if not os.path.isfile(path):
        return None
    out, key, body = {"subjects": {}}, None, []
    def flush():
        if key is None:
            return
        text = "\n".join(body).strip()
        if key.startswith("subject "):
            out["subjects"][key[8:].strip().lower()] = text
        else:
            out[key] = text
    for line in strip_comments(open(path, encoding="utf-8").read()).splitlines():
        m = re.match(r"^\[([^\]]+)\]\s*$", line.strip())
        if m:
            flush()
            key, body = m.group(1).strip().lower(), []
        elif key is not None:
            body.append(line)
    flush()
    return out


def prompt_tight(c, cam_block, action, brief, refs, here, aliases, prefix, music):
    """the same scene as v1, built to fit inside the documented prompt length"""
    items = (refs or {}).get("images", []) + (refs or {}).get("videos", [])
    subs, defs, unused, ret = {}, [], [], []
    for i in items:
        if i["kind"] in ABSENT and i["tag"] in here:
            subs[i["tag"]] = "<Subject %d>" % (len(subs) + 1)
    for i in items:
        tag, slugk = i["tag"], i["slug"].lower()
        text = brief["subjects"].get(slugk)
        if tag in subs:
            text = text or "{S} is %s, shown in {P}." % i["slug"]
            defs.append(text.replace("{S}", subs[tag]).replace("{P}", tag))
            ret.append("%s (%s): %s" % (tag, subs[tag], SHORT[i["kind"]]))
        elif i["kind"] in ABSENT:
            unused.append(tag)
        elif tag in here or slugk not in aliases:
            # a place or a style board: no <Subject n>, and only the place this
            # shot is set in - the other one is 700 characters of nothing
            if text:
                defs.append(text.replace("{P}", tag))
            ret.append("%s: %s" % (tag, SHORT.get(i["kind"], "partially_preserved.")))
        else:
            unused.append(tag)
    if unused:
        defs.append("%s: not used in this shot." % ", ".join(unused))
        ret.append("%s: %s" % (", ".join(unused), SHORT_ABSENT))
    tag = (refs or {}).get("scene_audio_tag")
    if tag:
        ret.append("%s: partially_copy - reused as the audience-only score." % tag)
    summary = prefix + (c.get("summary") or first_sentences(c["shot1"]))
    if c.get("lyrics"):
        summary += ' The lyric sung here is "%s".' % c["lyrics"]
    body = [
        ("subject_definitions", "\n".join("\n".join(wrap(d, 78)) for d in defs)),
        ("summary", summary),
        ("retention_analysis", "\n".join(ret)),
        ("detailed_description",
         brief["style"] + "\n\n[Shot 1] " + cam_block + "\n\n" + action),
        ("overall_soundscape", brief["sound"]),
        ("non_diegetic_music", music),
    ]
    return "\n\n".join("%s\n%s" % (k, indent(v)) for k, v in body) + "\n"


def summary_prefix(refs):
    """H3's summary opens with the task types the references actually perform."""
    kinds = []
    if not refs or refs.get("images") or refs.get("videos"):
        kinds.append("reference generation")
    if not refs or refs.get("scene_audio_tag"):
        kinds.append("audio reuse")
    return "[%s] " % " + ".join(kinds)


def retention_lines(refs, present=None):
    """one line per reference label, with H3's fixed relationship markers.
    `present` is the set of tags this shot actually uses; the rest are declared
    absent instead of preserved."""
    if not refs:
        return ["<Picture 1>: fully_preserved - the character reference.",
                "<Audio 1>: partially_copy - the supplied window of the song is "
                "reused as the audience-only score; the ambience below is added "
                "over it."]
    out = []
    for i in refs.get("images", []) + refs.get("videos", []):
        table = RETENTION
        if present is not None and i["tag"] not in present and i["kind"] in ABSENT:
            table = ABSENT
        marker, why = table.get(i["kind"], ("partially_preserved", "as defined above."))
        out.append("%s (%s, %s): %s - %s" % (i["tag"], i["slug"], i["kind"], marker, why))
    tag = refs.get("scene_audio_tag")
    if tag:
        out.append("%s: partially_copy - the supplied window of the song is reused "
                   "as the audience-only score for this clip; the diegetic ambience "
                   "described below is added over it and nothing else is." % tag)
    return out


def split_tail(tail):
    """tail.txt may label its two halves; without labels it is all diegetic."""
    parts, cur = {}, None
    for line in tail.splitlines():
        m = re.match(r"^\s*\[?(overall_soundscape|non_diegetic_music)\]?\s*:?\s*$",
                     line.strip(), re.I)
        if m:
            cur = m.group(1).lower()
            parts[cur] = []
        elif cur:
            parts[cur].append(line)
    if not parts:
        return tail, MUSIC_DEFAULT
    return ("\n".join(parts.get("overall_soundscape", [])).strip(),
            "\n".join(parts.get("non_diegetic_music", [])).strip() or MUSIC_DEFAULT)


def indent(text, n=2):
    pad = " " * n
    return "\n".join(pad + l if l.strip() else "" for l in text.splitlines())


def first_sentences(text, k=2):
    bits = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(bits[:k]).strip()


GERMAN = set("der die das den dem des und oder nicht sich ist sind wird werden "
             "auf mit von zu im in ein eine einen einem eines aus bei nach vor "
             "man sie er es wie noch nur auch dann dass wir uns ihre seinen".split())


FRAMING = re.compile(
    r"\b(close ?-?ups?|close on|tight on|wide on|wide shot|medium shot|full shot|"
    r"over[- ]the[- ]shoulder|over[- ]shoulder|front on|side on|top down|locked off|"
    r"the camera|dolly|pan left|pan right|tilt up|tilt down|zoom|push in|pull out|"
    r"bird'?s eye|worm'?s eye|dutch angle)\b", re.I)


def non_english(text):
    """crude: share of words that are German function words. English prose scores
    ~0, screenplay German scores well over the threshold."""
    words = re.findall(r"[a-zA-ZäöüÄÖÜß]+", text.lower())
    if len(words) < 12:
        return 0.0
    return sum(1 for w in words if w in GERMAN) / float(len(words))


def tc(s):
    s = float(s)
    return "%02d:%06.3f" % (int(s) // 60, s % 60)


def slug(t, cap=34):
    s = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "scene"
    if len(s) > cap:                      # filenames stay usable
        s = s[:cap].rsplit("-", 1)[0] or s[:cap]
    return s.strip("-")


def shots_of(c):
    out, i = [c.get("shot1") or ""], 2
    while (c.get("shot%d" % i) or "").strip():
        out.append(c["shot%d" % i]); i += 1
    return [x.strip() for x in out]


def action_of(c, cuts):
    """identical in every variant of a scene - that is the whole point of v1/v2/v3"""
    shots = shots_of(c)
    out = shots[0]
    for k, shot in enumerate(shots[1:]):
        if k >= len(cuts) or cuts[k] <= 0:
            break
        out += "\n\n[Shot %d] At 00:%06.3f, the shot cuts to:\n%s" % (
            k + 2, cuts[k], shot)
    return out


def cuts_of(r):
    raw = (r.get("inner_cuts") or "").strip()
    if raw:
        return [float(x) for x in raw.split(",") if x.strip()]
    one = float(r.get("inner_cut_rel") or 0)
    return [one] if one > 0 else []


def prompt_for(c, cam_block, action, bible, style, sound, music, refs, retention,
               prefix):
    summary = prefix + (c.get("summary") or first_sentences(c["shot1"]))
    if c.get("lyrics"):
        summary += ' The lyric sung here is "%s".' % c["lyrics"]
    # H3 wants the style established before [Shot 1], not in retention_analysis
    opening = style + (
        "\n\nHold identical across every scene of this film: the colour model, the\n"
        "line weight, the proportions and the costume of every character named\n"
        "above, and the time of day and weather of the location.")
    body = [
        ("subject_definitions",
         "References supplied with this generation:\n" +
         "\n".join("  " + l for l in refs) + "\n\n" + bible),
        ("summary", summary),
        ("retention_analysis", "\n".join(retention)),
        ("detailed_description",
         opening + "\n\n[Shot 1] " + cam_block + "\n\n" + action),
        ("overall_soundscape", sound),
        ("non_diegetic_music", music),
    ]
    return "\n\n".join("%s\n%s" % (k, indent(v)) for k, v in body) + "\n"


def write_batch_lists(song, rows, content, cams):
    """Index files for in-graph batching: one path per line, relative to the song
    folder so the deliverable survives being moved or copied to another machine.
    Prompts and audio in the same order, grouped by frame count so `length` is
    set once per group instead of per scene."""
    d = os.path.join(song, "__batch")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    groups, silent = {}, []
    for r in rows:
        n = int(r["scene"]); sl = slug(content[r["scene"]]["title"])
        if str(r.get("start", "")).strip() in ("", "-"):
            silent.append("%02d_%s" % (n, sl))   # no audio, so it cannot be paired
            continue
        for tag in sorted(cams):
            groups.setdefault((int(r["frames"]), tag), []).append(
                ("%02d_%s-%s.txt" % (n, sl, tag), "%02d_%s.mp3" % (n, sl)))
    lines = []
    for (frames, tag), items in sorted(groups.items()):
        base = "f%d-%s" % (frames, tag)
        for kind, idx in (("prompts", 0), ("audio", 1)):
            with open(os.path.join(d, "%s-%s.txt" % (base, kind)), "w",
                      encoding="utf-8", newline="\n") as fh:
                for it in items:
                    fh.write(it[idx] + "\n")
        lines.append((frames, tag, len(items)))
    with open(os.path.join(d, "__README.txt"), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write("Index files for batching this folder through ComfyUI.\n"
                 "Each pair is line-for-line aligned: line N of -prompts.txt is the\n"
                 "prompt for line N of -audio.txt. One pair per frame count, so you\n"
                 "set `length` once per group.\n\n")
        fh.write("%-22s %-8s %s\n" % ("group", "length", "queue batch count"))
        for frames, tag, count in lines:
            fh.write("%-22s %-8d %d\n" % ("f%d-%s" % (frames, tag), frames, count))
        if silent:
            fh.write("\nNOT in these lists, because they have no audio to pair with:\n"
                     "  %s\nRender them on their own.\n" % ", ".join(silent))
        fh.write("\nWiring, and why core nodes are not enough: see docs/comfyui-batch.md\n"
                 "Paths are relative to the song folder - the one directly above this\n"
                 "one. Prefix them with wherever that folder lives on the machine that\n"
                 "runs ComfyUI.\n")
    return lines


FPS = 24            # H3 renders at 24 fps regardless of the screenplay's own rate

SILENT_MUSIC = ("There is NO music in this clip. The song has not started yet. Leave\n"
                "the track empty and let the location sound above carry it alone.")


def main():
    song = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "."
    name = os.path.basename(os.path.abspath(song))
    SRC = os.path.join(song, "_source")
    R = lambda p: strip_comments(open(os.path.join(SRC, p), encoding="utf-8").read())
    bible, style, tail = R("bible.txt"), R("style.txt"), R("tail.txt")
    synopsis = R("synopsis.txt").strip() if os.path.isfile(
        os.path.join(SRC, "synopsis.txt")) else ""
    sound, music = split_tail(tail)
    content = json.load(open(os.path.join(SRC, "content.json"), encoding="utf-8"))
    rows = list(csv.DictReader(open(os.path.join(SRC, "scenes.tsv"), encoding="utf-8"),
                              delimiter="\t"))
    CAM = read_cameras(SRC)
    refs = read_refs(song)
    rlines = ref_lines(refs)
    prefix = summary_prefix(refs)
    mute = dict(refs or {}, scene_audio_tag=None)
    rlines_q, prefix_q = ref_lines(mute), summary_prefix(mute)
    aliases = read_aliases(SRC)
    brief = read_brief(SRC)

    # scenes with no content.json entry fall back to the screenplay in scenes.tsv,
    # so a drehbuch run produces usable prompts with no drafting pass at all
    from_screenplay = 0
    for r in rows:
        if r["scene"] in content:
            continue
        desc = (r.get("screenplay") or "").split(" || ")
        if not desc[0].strip():
            sys.exit("scene %s has neither a content.json entry nor screenplay text"
                     % r["scene"])
        entry = {"title": r.get("title") or "scene %s" % r["scene"],
                 "lyrics": r.get("lyrics_screenplay") or ""}
        for k, part in enumerate(desc, 1):
            entry["shot%d" % k] = part.strip()
        content[r["scene"]] = entry
        from_screenplay += 1

    elements = 0
    for k in sorted((k for k in content if k not in {r["scene"] for r in rows}),
                    key=lambda x: int(x)):
        fr = content[k].get("frames")
        if not fr:
            continue
        rows.append({"scene": k, "start": "-", "end": "-", "frames": str(int(fr)),
                     "duration": "%.4f" % (int(fr) / float(FPS)), "tl_frame": "-",
                     "inner_cut_rel": "0.000", "inner_cuts": "", "continuity": "",
                     "framing": "", "screenplay": ""})
        elements += 1

    for f in os.listdir(song):                      # clear previous generated output
        if re.match(r"^\d\d_.*-v\d\.txt$", f) or f in ("ALL_scenes.txt", "__SCENES.tsv"):
            os.remove(os.path.join(song, f))
    shutil.rmtree(os.path.join(song, "variants"), ignore_errors=True)

    per_scene_cams = 0
    bad_cam = set()
    cast = []
    longest = {}
    dsl = ["# %s - all %d scenes in one file, in the storyboard DSL.\n"
           "# This is the ComfyUI node's batch input. The NN_*.txt files beside it\n"
           "# are the same material as finished H3 prompts, for pasting by hand.\n"
           "# Point the storyboard node here and set batch count = %d.\n"
           % (name.upper(), len(rows), len(rows)),
           "@BIBLE\n" + bible, "\n@STYLE\n" + style]
    manifest = [["scene", "song_start", "song_end", "tl_frame", "frames", "duration",
                 "inner_cuts", "continuity", "audio", "prompts", "lyrics"]]
    n_var = 0

    for r in rows:
        n = int(r["scene"]); c = content[r["scene"]]
        silent = str(r.get("start", "")).strip() in ("", "-")
        cuts, dur = cuts_of(r), float(r["duration"])
        cut = cuts[0] if cuts else 0.0
        action = action_of(c, cuts)
        sl = slug(c["title"])
        declared = c.get("cast")
        here = present_tags(refs, c["title"] + " " + action, aliases,
                            None if declared is None
                            else {s.lower() for s in declared})
        cast.append((n, here))
        RL, RT, PF = (rlines_q, retention_lines(mute, here), prefix_q) if silent \
            else (rlines, retention_lines(refs, here), prefix)

        # a scene may carry its own cameras: v1 is the screenplay's framing, the
        # rest is coverage. Anything it does not define falls back to the template.
        own = c.get("cameras") or {}
        tags = sorted(set(CAM) | set(own) | ({"v4"} if brief else set()))
        for tag in tags:
            # v4 is not a fourth angle - it is v1's shot, built short
            src_tag = "v1" if tag == "v4" and "v4" not in own else tag
            cam = (own.get(src_tag) or "").strip() \
                or (CAM[src_tag][1] if src_tag in CAM else "")
            if not cam:
                continue
            cam = camera_sentence(cam, bad_cam)
            mus = SILENT_MUSIC if silent else music
            mus_short = SILENT_MUSIC if silent else (brief or {}).get("music") or music
            text = prompt_tight(c, cam, action, brief, refs, here, aliases,
                                PF, mus_short) \
                if tag == "v4" else \
                prompt_for(c, cam, action, bible, style, sound, mus, RL, RT, PF)
            open(os.path.join(song, "%02d_%s-%s.txt" % (n, sl, tag)),
                 "w", encoding="utf-8", newline="\n").write(text)
            longest[tag] = max(longest.get(tag, 0), len(text))
            n_var += 1
        if own:
            per_scene_cams += 1

        dsl.append("\n@SCENE %s-%s | %s%s\n%s"
                   % (tc(0.0) if silent else tc(r["start"]),
                      tc(dur) if silent else tc(r["end"]), c["title"],
                      "   # no audio - render this one on its own" if silent else "",
                      action))
        manifest.append([
            "%02d" % n, "-" if silent else tc(r["start"]),
            "-" if silent else tc(r["end"]), r.get("tl_frame", "-"),
            r["frames"], "%.4f" % dur,
            ",".join("%.3f" % x for x in cuts) or "-",
            r.get("continuity") or "-", "%02d_%s.mp3" % (n, sl),
            " ".join("%02d_%s-%s.txt" % (n, sl, t) for t in tags),
            c["lyrics"] or "(instrumental)"])

    dsl.append("\n@TAIL\n" + tail + "\n")
    open(os.path.join(song, "ALL_scenes.txt"), "w", encoding="utf-8",
         newline="\n").write("\n".join(dsl))
    with open(os.path.join(song, "__SCENES.tsv"), "w", encoding="utf-8",
              newline="\n") as fh:
        for row in manifest:
            fh.write("\t".join(row) + "\n")

    # An element scene exists only in content.json, so split_audio never sees it
    # and it would be the one row of the manifest with no audio - which is exactly
    # what takes down the first job of a batch run. Give it silence too.
    import subprocess
    silenced = 0
    for r in rows:
        if str(r.get("start", "")).strip() not in ("", "-"):
            continue
        n = int(r["scene"])
        dst = os.path.join(song, "scene_%02d.mp3" % n)
        final = os.path.join(song, "%02d_%s.mp3"
                             % (n, slug(content[r["scene"]]["title"])))
        if os.path.isfile(final) or os.path.isfile(dst):
            continue
        try:
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y",
                            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                            "-t", "%.4f" % (int(r["frames"]) / float(FPS)),
                            "-c:a", "libmp3lame", "-q:a", "9", dst], check=True)
            silenced += 1
        except (OSError, subprocess.CalledProcessError):
            print("! could not write a silent slice for scene %02d (no ffmpeg?) - "
                  "an audio loader will refuse that scene" % n)

    # name each audio slice after its prompt file so the pair sits together
    renamed = 0
    for r in rows:
        n = int(r["scene"]); c = content[r["scene"]]
        dst = os.path.join(song, "%02d_%s.mp3" % (n, slug(c["title"])))
        # a fresh slice from split_audio always wins: re-cutting the song must
        # replace what is paired with the prompts, not be ignored because a
        # slice under that name happens to be lying there already
        fresh = [os.path.join(song, "scene_%02d.mp3" % n),
                 os.path.join(song, "audio", "scene_%02d.mp3" % n)]
        # otherwise a renamed scene leaves its slice behind under the old slug
        stale = sorted(os.path.join(song, f) for f in os.listdir(song)
                       if re.match(r"^%02d_.*\.mp3$" % n, f)
                       and os.path.join(song, f) != dst)
        for cand in fresh + ([] if os.path.exists(dst) else stale):
            if os.path.exists(cand):
                os.replace(cand, dst); renamed += 1; break
    adir = os.path.join(song, "audio")
    if os.path.isdir(adir) and not os.listdir(adir):
        os.rmdir(adir)

    batch = write_batch_lists(song, rows, content,
                              dict(CAM, v4=("short", "")) if brief else CAM)

    total = sum(float(r["duration"]) for r in rows)
    sung = [r for r in rows if str(r.get("start", "")).strip() not in ("", "-")]
    span = max(float(r["end"]) for r in sung) - min(float(r["start"]) for r in sung)
    readme = ["%s - %d scenes over %.1f s of song, %.1f s of clip material%s"
              % (name.upper(), len(rows), span, total,
                 " (scenes overlap - trim in the edit)" if total > span + 1 else ""),
              "=" * 74, ""]
    if synopsis:
        readme += ["WHAT HAPPENS", ""] + ["  " + l if l.strip() else ""
                                          for l in synopsis.splitlines()] + \
                  ["", "-" * 74, ""]
    readme += [
              "Every scene is one MiniMax H3 render. Files are paired by prefix:", "",
              "  NN_title.mp3      the exact window of the song for that scene",
              "  NN_title-v1.txt   the director's shot",
              "  NN_title-v2.txt   other angle, medium",
              "  NN_title-v3.txt   close / detail",
              "",
              "WHAT EACH VERSION IS FOR", "",
              "  v1  YOURS. Whatever framing the screenplay states is what v1 does -",
              "      `mvkit scenes` lifts it out of the Drehbuch into the framing column",
              "      and the build warns when v1 ignores it. If the screenplay says",
              "      over-the-shoulder at water level, that is v1. It is the shot you",
              "      wrote, not an interpretation of it.",
              "",
              "  v2  and",
              "  v3  COVERAGE, chosen by film practice rather than by the screenplay:",
              "      never repeat v1's size, cross the axis so the two cut together,",
              "      and give one of them something the master cannot hold - a face, a",
              "      hand, a point of contact. v2 is roughly ninety degrees off the",
              "      master and closer, v3 is the detail. See",
              "      templates/cameras/__COVERAGE.txt for the table they come from.",
              "",
              "      The ACTION text is byte-identical in v1, v2 and v3 - only the",
              "      camera differs. That is the point: they are three angles on ONE",
              "      moment, they share the single NN_title.mp3, and they can be cut",
              "      together inside the scene. They are not alternative takes.",
              "",]
    if brief:
        readme += [
              "  v4  THE SHORT BUILD, and an experiment. Same shot as v1, same camera,",
              "      same references - but assembled from _source/brief.txt instead of",
              "      the full bible and style, and carrying only the characters that are",
              "      actually in the scene. Roughly 6 KB against v1's 30 KB.",
              "      Every published H3 guide puts the prompt limit at 7,000 characters.",
              "      If that limit is real for ComfyUI too, then in v1 the model never",
              "      reaches the shot description at all - it stops inside the cast list",
              "      and improvises the rest, which is what stray characters and",
              "      vanishing scenery look like. UNTESTED. Render 01-v4 against 01-v1",
              "      and compare before believing either of them.",
              "",]
    readme += [
              "The -vN.txt files are finished H3 prompts: MiniMax's six sections, no",
              "markup, nothing to strip. Paste one in as the prompt exactly as it is.",
              "",
              "  __SCENES.tsv      frame count, timing and pairing for every scene",
              "  __batch/          line-aligned lists for batching in ComfyUI",
              "  ALL_scenes.txt    the same material in this kit's DSL, which is what",
              "                    the ComfyUI storyboard node reads for a batch run",
              "", "References to load, in this order:", ""]
    readme += ["  " + l for l in rlines]
    chained = [(r, content[r["scene"]]) for r in rows
               if "chain" in (r.get("continuity") or "")]
    if chained:
        readme += ["", "Scenes that continue the shot before them:", "",
                   "  The screenplay holds one camera setup across these. Render them in",
                   "  order, export the LAST frame of the preceding clip, and load it as the",
                   "  first-frame reference for the next - that is what keeps the drawing from",
                   "  changing mid-setup while there are no character references.", ""]
        for r, c_ in chained:
            n = int(r["scene"]); sl = slug(c_["title"])
            prev = [x for x in rows if int(x["scene"]) == n - 1]
            src = ("%02d_%s" % (n - 1, slug(content[prev[0]["scene"]]["title"]))
                   if prev else "the clip before it")
            readme.append("  %02d_%s   <- last frame of %s" % (n, sl, src))
        readme.append("")
    held = [r["scene"] for r in rows if "hold" in (r.get("continuity") or "")]
    if held:
        readme += ["Scenes that must end on the frame they started on (the screenplay",
                   "marks them First Frame <> Last Frame): " + ", ".join(held), ""]
    # scenes that carry a "composite" block: what is a plate, what is laid over it,
    # and what may be looped or held. The overlay is never rendered into the plate,
    # because it is assembled in the edit.
    comp = [(r["scene"], content[r["scene"]]["composite"]) for r in rows
            if content[r["scene"]].get("composite")]
    if comp:
        readme += ["", "COMPOSITING - assembled in the edit, not rendered in", ""]
        order = {"loop": 0, "plate": 1, "inset": 2, "element": 3, "freeze": 4}
        for scene, cp in sorted(comp, key=lambda x: (order.get(x[1].get("role"), 9), x[0])):
            sl = slug(content[scene]["title"])
            head = "  %02d_%s  [%s]" % (int(scene), sl, cp.get("role", "?"))
            if cp.get("with"):
                head += " -> over %02d" % int(cp["with"])
            readme.append(head)
            for k in ("where", "note"):
                if cp.get(k):
                    readme += ["        " + l for l in wrap(cp[k], 66)]
        readme += ["",
                   "  A plate is rendered with its overlay area left empty on purpose.",
                   "  An inset or element is a full-frame clip of its own - place, scale",
                   "  and fade it in the edit. An element has no audio and no place on the",
                   "  timeline; it exists only to be laid over something.",
                   "  Nothing here is burned into a render.", ""]

    howto = config(SRC, "comfyui.txt")
    if howto:
        readme += [""] + howto.replace("{song}", name).rstrip().splitlines() + [""]

    readme += ["",
               "Set length to the frame count in __SCENES.tsv - H3 only accepts lengths",
               "where frames % 17 == 5, and it rounds up, so do not retype it by feel.",
               "",
               "Do not edit these files - they are regenerated. Edit _source/ and re-run",
               "`mvkit build %s`." % name, ""]
    open(os.path.join(song, "__READ_ME.txt"), "w", encoding="utf-8",
         newline="\n").write("\n".join(readme))

    framed = sorted({r["scene"] for r in rows
                     for t in (content[r["scene"]].get("shot1"),
                               content[r["scene"]].get("shot2"))
                     if t and FRAMING.search(t)}, key=int)
    foreign = [r["scene"] for r in rows
               if non_english(" ".join(filter(None, (content[r["scene"]].get("shot1"),
                                                     content[r["scene"]].get("shot2"))))) > 0.12]
    print("scenes      : %d" % len(rows))
    if from_screenplay:
        print("from drehbuch: %d scene(s) had no content.json entry and used the "
              "screenplay text" % from_screenplay)
    try:
        import subprocess
        subprocess.run([sys.executable, os.path.join(KIT, "bin", "make_workflows.py"),
                        song], check=True)
    except Exception as e:                       # a broken generator must not
        print("! workflows not written (%s)" % e)   # cost you the deliverable

    if elements:
        print("elements    : %d clip(s) with no window of the song" % elements)
    if silenced:
        print("silence     : %d slice(s) written for scenes with no window of the song"
              % silenced)
    if renamed:
        print("audio pairs : %d slices renamed to match their prompt" % renamed)
    print("prompts     : %d  (six sections each)" % n_var)
    over = ", ".join("%s %d" % (k, v) for k, v in sorted(longest.items()) if v > 7000)
    print("longest     : %s chars"
          % ", ".join("%s %d" % kv for kv in sorted(longest.items())))
    if over:
        print("! over the 7000-character prompt length H3 documents: %s" % over)
        print("  UNTESTED whether ComfyUI truncates there - see CLAUDE.md. v4 is the")
        print("  short build; render it against v1 before restructuring anything.")
    print("cameras     : %d scene(s) carry their own, %d fall back to the template"
          % (per_scene_cams, len(rows) - per_scene_cams))
    print("manifest    : __SCENES.tsv")
    if refs and refs.get("images"):
        drawn = {}
        for n, here in cast:
            for t in here:
                drawn.setdefault(t, []).append(n)
        print("cast        : per scene, from the words in the action")
        missing = []
        for i in refs["images"] + refs.get("videos", []):
            if i["kind"] not in ABSENT:
                continue
            got = drawn.get(i["tag"], [])
            ns = ", ".join("%02d" % n for n in got[:14]) + (" ..." if len(got) > 14 else "")
            print("  %-12s %-22s %2d scene(s)%s"
                  % (i["tag"], i["slug"], len(got), ": " + ns if got else ""))
            if not got:
                missing.append(i["slug"])
        if missing:
            print("! never detected in any scene: %s" % ", ".join(missing))
            print("  Every scene will tell H3 not to draw them. Add the English words")
            print("  for them to _source/refs/__ALIASES.txt as `<slug>: word, word`.")
        empty = ["%02d" % n for n, here in cast if not here]
        if empty:
            print("! %d scene(s) name no character at all: %s"
                  % (len(empty), ", ".join(empty[:12])
                     + (" ..." if len(empty) > 12 else "")))
            print("  Those prompts tell H3 that every character is absent. Name who")
            print("  is in the shot in the action, or give the scene a \"cast\" list.")
    print("batch lists : __batch/  (%d groups: %s)"
          % (len(batch), ", ".join("f%d-%s x%d" % b for b in batch[:4])
             + (" ..." if len(batch) > 4 else "")))
    print("dsl         : ALL_scenes.txt  (for the ComfyUI node)")
    if foreign:
        print("! %d scene(s) still read as German, not English shot language: %s"
              % (len(foreign), ", ".join(foreign[:12]) + (" ..." if len(foreign) > 12 else "")))
        print("  H3 follows English far better. Run `mvkit draft <song> --llm --force`,")
        print("  or rewrite those entries in _source/content.json. Lyrics stay verbatim.")
    ignored = [r["scene"] for r in rows
               if (r.get("framing") or "").strip()
               and not ((content[r["scene"]].get("cameras") or {}).get("v1") or "").strip()]
    if ignored:
        print("! %d scene(s) have a framing in the screenplay that v1 does not use: %s"
              % (len(ignored), ", ".join(ignored[:12])
                 + (" ..." if len(ignored) > 12 else "")))
        print("  v1 is meant to be the director's shot. Put it in content.json as")
        print("  \"cameras\": {\"v1\": \"...\"} - see templates/cameras/__COVERAGE.txt.")
    if framed:
        print("! %d scene(s) name a framing in the action: %s"
              % (len(framed), ", ".join(framed[:12]) + (" ..." if len(framed) > 12 else "")))
        print("  The action is reused by v1/v2/v3 verbatim, so a framing there")
        print("  contradicts two of the three. Leave it to the camera block.")
    if bad_cam:
        print("! unknown camera token(s), dropped from the prompt: %s"
              % ", ".join(sorted(bad_cam)))
        print("  Use the vocabulary in templates/cameras/__GLOSSARY.txt.")
    # synopsis.txt is written by an agent reading the screenplay, not derived from
    # it by this script. So the script cannot keep it true - it can only say when
    # it has gone stale and needs re-reading.
    sp, dp = os.path.join(SRC, "synopsis.txt"), os.path.join(SRC, "drehbuch.txt")
    if os.path.isfile(sp) and os.path.isfile(dp) \
            and os.path.getmtime(dp) > os.path.getmtime(sp) + 1:
        print("! synopsis.txt is older than drehbuch.txt")
        print("  It is written, not generated. Re-read the screenplay and rewrite it;")
        print("  do not assume the summary still matches.")
    elif not os.path.isfile(sp) and os.path.isfile(dp):
        print("! no _source/synopsis.txt - the deliverable has no plain-language summary")

    if refs and refs.get("warnings"):
        for w in refs["warnings"]:
            print("! refs: %s" % w)


if __name__ == "__main__":
    main()

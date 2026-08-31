#!/usr/bin/env python3
"""Write the three starting ComfyUI workflows into a song folder.

  make_workflows.py <song-dir> [--h3-class NAME] [--h3-images N]
                    [--audio-class NAME] [--image-class NAME] [--save-class NAME]

  __workflow_upscale.json  the pass after rendering: a folder of clips through a
                           4x line-art model. Complete and standalone.
  __workflow_song.json     written by --from: YOUR H3 graph with a song folder
                           wired into it. The render workflow.

The H3 node returns `positive` and `LATENT`, not a video, so there is no point
generating a render graph from scratch - the model, sampler and settings cannot be
guessed. Hand it one that works instead:

    make_workflows.py <song-dir> --from your_workflow.json

A workflow saved from the ComfyUI menu is converted to API format on the way in,
so either format is fine.

Stdlib only.
"""
import argparse
import json
import os
import re
import sys


def nat(name):
    """sort ref_image_0 before ref_image_10, and image2 before image10"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def image_slots(inputs):
    """reference-image inputs, whatever they are called.

    The real node names them ref_image_0, ref_image_1, ... (0-based, and the
    input is dynamic - connecting one makes the next appear). Older guesses used
    image1..image9. Match either - but only names that END in a number, or
    `ref_image_size` gets treated as a slot and an image loader wired into a
    combo widget.
    """
    # the real node namespaces them: "ref_images.ref_image_0". Match the last
    # segment, and only names ending in a number so ref_image_size is excluded.
    return sorted((k for k in inputs
                   if re.match(r"^(ref_)?image_?\d+$", k.lower().rsplit(".", 1)[-1])),
                  key=nat)


def audio_slot(inputs):
    """where a STANDALONE audio reference goes.

    Not ref_video_audio_*: that is the soundtrack of a reference video, and it
    claims an <Audio> number before any standalone audio. Putting the song slice
    there would be wrong twice over.
    """
    cands = [k for k in inputs
             if re.match(r"^(ref_)?audio_?\d*$", k.lower().rsplit(".", 1)[-1])
             and "video" not in k.lower()]
    return sorted(cands, key=nat)[0] if cands else None

H3_CLASS = "MiniMaxH3ReferenceToVideo"   # confirmed against a running server
H3_IMAGES = 9
AUDIO_CLASS = "VHS_LoadAudio"
AUDIO_FIELD = "audio_file"
IMAGE_CLASS = "VHS_LoadImagePath"
IMAGE_FIELD = "path"
SAVE_CLASS = "SaveVideo"
# One 4x line-art model, and whatever it produces is what gets written. No
# rescaling in the graph: hitting 4K exactly is the edit's job.
UPSCALE_MODEL = "RealESRGAN_x4plus_anime_6B.pth"
# HurricaneSongFolder's outputs, in order. Referenced by name everywhere so
# trimming the node does not silently rewire a graph to the wrong socket.
SONG_OUTPUTS = ("prompt", "audio_path", "frames", "scene_count", "save_prefix")


def song_out(name):
    return SONG_OUTPUTS.index(name)
VIDEO_LOAD = "VHS_LoadVideoPath"
VIDEO_COMBINE = "VHS_VideoCombine"
# Not a placeholder any more - the class name is confirmed. What IS incomplete is
# the graph: this node returns positive/LATENT, so a model loader, a sampler, a
# VAE decode and a video output have to come from somewhere, and none of them can
# be guessed. `--from your_export.json` keeps yours.
NOTE = ("this node conditions a sampler - it returns positive/LATENT, not a "
        "video. Attach your own model/sampler/VAEDecode chain, or better: "
        "`mvkit workflows <song> --from your_api_export.json`")


ABS = re.compile(r"^(?:/(?:Users|home|Volumes|mnt|media)/|[A-Za-z]:[\\/]|\\\\)")


def find_abs_paths(graph):
    """-> [(node, input, value)] for anything that looks like an absolute path.

    ComfyUI usually runs somewhere else than this kit - another machine, another
    OS - so a path written here is wrong there. Better an empty field the user
    fills than a path that silently points at nothing.
    """
    bad = []
    for nid, n in sorted(graph.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        for k, v in (n.get("inputs") or {}).items():
            if isinstance(v, str) and ABS.match(v.strip()):
                bad.append((nid, k, v))
    return bad


def read_refs(song):
    """-> [(tag, label, abs path)] for the reference sheets, in slot order"""
    rj = os.path.join(song, "_source", "refs.json")
    if not os.path.isfile(rj):
        return []
    with open(rj, encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for i in data.get("images", []):
        # refs.json's `file` is ALREADY relative to the song folder
        # ("_source/refs/01_....png"), so joining the refs dir again doubles it
        rel = i.get("file", "")
        out.append((i.get("tag", ""),
                    "%s %s (%s)" % (i.get("tag", ""), i.get("slug", ""),
                                    i.get("kind", "")),
                    rel, os.path.basename(rel)))
    return out


def save_node(a, prefix):
    """Configured but NOT connected: its `video` input is left open because the
    H3 node returns positive/LATENT, and wiring a save to a CONDITIONING output
    would be worse than leaving it obviously unfinished. Attach the output of
    your VAEDecode here. `filename_prefix` is already driven, which is the part
    worth having: renders arrive grouped per song and named after their prompt.
    """
    return {"class_type": a.save_class,
            "inputs": {"filename_prefix": prefix},
            "_meta": {"title": "SAVE - connect your VAEDecode to `video`"}}


# UI-only inputs: they exist so the browser can draw an upload button and are not
# part of what /prompt accepts
UI_ONLY = ("IMAGEUPLOAD", "AUDIOUPLOAD", "AUDIO_UI", "VIDEOUPLOAD")


def ui_to_api(ui):
    """Convert a saved UI workflow to the flat API format /prompt accepts.

    Doable without asking a server, because the UI file names every input: each
    entry in `inputs` carries a name, and the ones with a `widget` key take their
    value from `widgets_values` positionally, in order. Muted and bypassed nodes
    and notes are dropped.
    """
    src = {}
    for l in ui.get("links", []):          # [id, from_node, from_slot, to, slot, type]
        if isinstance(l, list) and len(l) >= 3:
            src[l[0]] = (str(l[1]), l[2])
    out = {}
    for n in ui.get("nodes", []):
        t = n.get("type", "")
        if n.get("mode") in (2, 4) or t in ("Note", "MarkdownNote", "Reroute"):
            continue
        ins, widgets = {}, list(n.get("widgets_values") or [])
        wi = 0
        for i in (n.get("inputs") or []):
            name, ityp = i.get("name"), (i.get("type") or "")
            if i.get("widget"):
                if wi < len(widgets):
                    v = widgets[wi]
                    if ityp.upper() not in UI_ONLY:
                        ins[name] = v
                    wi += 1
            if i.get("link") is not None and i["link"] in src:
                ins[name] = list(src[i["link"]])
        out[str(n["id"])] = {"class_type": t, "inputs": ins,
                             "_meta": {"title": n.get("title") or t}}
    return out


# nodes that are an end in themselves; everything else only matters if it feeds one
OUTPUT_CLASSES = re.compile(r"^(Save|Preview|VHS_VideoCombine|SaveAudio|SaveVideo)",
                            re.I)


def prune_unreachable(graph):
    """Drop nodes that no longer reach an output, and say which.

    Wrapping displaces whatever used to feed the H3 node - the prompt primitive,
    the LoadImage nodes, the LoadAudio. ComfyUI would not execute them, but they
    sit in the graph looking connected and are the first thing you misread when
    you open it. Removing them is the difference between a graph you can read and
    one you have to squint at.
    """
    outs = [nid for nid, n in graph.items()
            if OUTPUT_CLASSES.match(n.get("class_type", ""))]
    if not outs:
        return graph, []                       # nothing recognisable to walk back from
    keep, stack = set(), list(outs)
    while stack:
        nid = stack.pop()
        if nid in keep or nid not in graph:
            continue
        keep.add(nid)
        for v in (graph[nid].get("inputs") or {}).values():
            if isinstance(v, list) and v and isinstance(v[0], str):
                stack.append(v[0])
    dropped = [(nid, graph[nid].get("class_type", "?"),
                (graph[nid].get("_meta") or {}).get("title", ""))
               for nid in sorted(graph, key=lambda x: int(x) if x.isdigit() else 0)
               if nid not in keep]
    return {k: v for k, v in graph.items() if k in keep}, dropped


# UI-form socket definitions for the two nodes we insert. Written out rather than
# lifted from some other graph, because a donor file can be missing or stale and a
# node with `outputs: []` produces links that point at sockets that do not exist.
SONG_NODE_DEF = {
    "type": "HurricaneSongFolder", "flags": {}, "order": 0, "mode": 0,
    "properties": {"Node name for S&R": "HurricaneSongFolder"},
    "size": [300, 150],
    "inputs": [
        {"name": "song_path", "type": "STRING", "widget": {"name": "song_path"}},
        {"name": "scene_index", "type": "INT", "widget": {"name": "scene_index"}},
        {"name": "variant", "type": "COMBO", "widget": {"name": "variant"}},
        {"name": "out_subfolder", "type": "STRING",
         "widget": {"name": "out_subfolder"}},
    ],
    "outputs": [{"name": n, "localized_name": n, "type": t, "links": []}
                for n, t in (("prompt", "STRING"), ("audio_path", "STRING"),
                             ("frames", "INT"), ("scene_count", "INT"),
                             ("save_prefix", "STRING"))],
    "widgets_values": ["", 1, "v1", ""],
}

AUDIO_NODE_DEF = {
    "type": "VHS_LoadAudio", "flags": {}, "order": 0, "mode": 0,
    "properties": {"Node name for S&R": "VHS_LoadAudio"}, "size": [280, 80],
    "inputs": [
        {"name": "audio_file", "type": "STRING", "widget": {"name": "audio_file"}},
        {"name": "seek_seconds", "type": "FLOAT", "widget": {"name": "seek_seconds"}},
        {"name": "duration", "type": "FLOAT", "widget": {"name": "duration"}},
    ],
    "outputs": [{"name": "audio", "localized_name": "audio", "type": "AUDIO",
                 "links": []},
                {"name": "duration", "localized_name": "duration", "type": "FLOAT",
                 "links": []}],
    "widgets_values": ["", 0.0, 0.0],
}


def wrap_ui(ui, song, a):
    """Put the song folder into a UI workflow, keeping its layout and groups.

    The API format has no positions and no groups, so going through it throws the
    overview away. This edits the UI file in place instead: it removes only the
    nodes that fed the three inputs a song folder now drives, drops the ones that
    only fed those, and puts ours where they sat.
    """
    nodes = {n["id"]: n for n in ui.get("nodes", [])}
    links = {l[0]: l for l in ui.get("links", [])}
    h3 = next((n for n in nodes.values()
               if n.get("type") == a.h3_class
               or (n.get("type", "").find("MiniMax") >= 0
                   and any(i.get("name") == "length" for i in (n.get("inputs") or [])))),
              None)
    if not h3:
        sys.exit("no H3 node in that workflow (looked for %r and for a MiniMax node "
                 "with a `length` input)" % a.h3_class)

    def feeder(name):
        for i in (h3.get("inputs") or []):
            if i.get("name") == name and i.get("link") in links:
                return links[i["link"]][1]
        return None

    a_slot = audio_slot({i["name"]: 1 for i in (h3.get("inputs") or [])})
    displaced = {feeder("prompt"), feeder("length")}
    if a_slot:
        displaced.add(feeder(a_slot))
    displaced.discard(None)

    # whatever only ever fed a displaced node is displaced too - the duration
    # float behind the length expression, for instance. Nothing else: a node with
    # any other consumer, or none at all, is left where the user put it.
    consumers = {}
    for l in ui.get("links", []):
        consumers.setdefault(l[1], set()).add(l[3])
    grew = True
    while grew:
        grew = False
        for i, dsts in consumers.items():
            if i not in displaced and dsts and dsts <= displaced:
                displaced.add(i)
                grew = True

    nid = max(nodes) + 1
    lid = max(links) + 1 if links else 1

    DEFS = {"HurricaneSongFolder": SONG_NODE_DEF, "VHS_LoadAudio": AUDIO_NODE_DEF}

    def place(kind, pos):
        nonlocal nid
        n = json.loads(json.dumps(DEFS[kind]))
        n["id"] = nid
        n["pos"] = list(pos)
        for o in (n.get("outputs") or []):
            o["links"] = []
        for i in (n.get("inputs") or []):
            i.pop("link", None)
        nid += 1
        return n

    where = lambda i: nodes[i]["pos"] if i in nodes else [0, 0]
    song_n = place("HurricaneSongFolder", where(feeder("prompt")))
    song_n["title"] = "SONG - set song_path"
    aud_n = place("VHS_LoadAudio", where(feeder(a_slot)) if a_slot else [0, 0])
    aud_n["title"] = "AUDIO - this scene's slice"

    def out_index(n, name):
        for k, o in enumerate(n.get("outputs") or []):
            if o.get("name") == name:
                return k
        sys.exit("node %s has no output named %r - the socket definition and the "
                 "node have drifted apart" % (n.get("type"), name))

    def connect(src, sname, dst, dname, typ):
        nonlocal lid
        si = out_index(src, sname)
        for i in (dst.get("inputs") or []):
            if i.get("name") == dname:
                i["link"] = lid
                break
        else:
            dst.setdefault("inputs", []).append(
                {"name": dname, "type": typ, "link": lid})
        outs = src.setdefault("outputs", [])
        if si < len(outs):
            outs[si].setdefault("links", []).append(lid)
        ui["links"].append([lid, src["id"], si, dst["id"],
                            next((k for k, i in enumerate(dst["inputs"])
                                  if i.get("name") == dname), 0), typ])
        lid += 1

    connect(song_n, "prompt", h3, "prompt", "STRING")
    connect(song_n, "frames", h3, "length", "INT")
    connect(song_n, "audio_path", aud_n, "audio_file", "STRING")
    if a_slot:
        connect(aud_n, "audio", h3, a_slot, "AUDIO")
    saves = [n for n in nodes.values()
             if OUTPUT_CLASSES.match(n.get("type", ""))
             and any(i.get("name") == "filename_prefix" for i in (n.get("inputs") or []))]
    for sv in saves:
        connect(song_n, "save_prefix", sv, "filename_prefix", "STRING")

    # the sheets are constant per song: leave their loaders, retitle them
    refs = read_refs(song)
    slots = image_slots({i["name"]: 1 for i in (h3.get("inputs") or [])})
    retitled = 0
    for k, slot in enumerate(slots):
        src = feeder(slot)
        if src in nodes and k < len(refs):
            nodes[src]["title"] = refs[k][1]
            retitled += 1

    keep = [n for n in ui["nodes"] if n["id"] not in displaced]
    ui["nodes"] = keep + [song_n, aud_n]
    alive = {n["id"] for n in ui["nodes"]}
    ui["links"] = [l for l in ui["links"] if l[1] in alive and l[3] in alive]
    live_links = {l[0] for l in ui["links"]}
    for n in ui["nodes"]:
        for i in (n.get("inputs") or []):
            if i.get("link") not in live_links:
                i.pop("link", None)
        for o in (n.get("outputs") or []):
            o["links"] = [x for x in (o.get("links") or []) if x in live_links]
    ui["last_node_id"] = max(nid, ui.get("last_node_id", 0))
    ui["last_link_id"] = max(lid, ui.get("last_link_id", 0))

    report = ["replaced %d node(s) that fed prompt/length/audio: %s"
              % (len(displaced), ", ".join("%s %s" % (i, nodes[i].get("type"))
                                           for i in sorted(displaced) if i in nodes)),
              "reference sheets left alone; %d loader(s) retitled with their tag"
              % retitled,
              "save prefix driven on %d node(s)" % len(saves),
              "layout and %d group(s) kept" % len(ui.get("groups") or [])]
    return ui, report


def find_h3_in(graph, h3_class):
    """the H3 node inside a graph the user exported themselves"""
    for nid, n in graph.items():
        if n.get("class_type") == h3_class:
            return nid
    # fall back on shape: a prompt and a length is the H3 node in practice
    for nid, n in graph.items():
        ins = n.get("inputs", {})
        if "prompt" in ins and "length" in ins:
            return nid
    return None


def wrap(raw, song, a):
    """Take a graph exported from ComfyUI and put our nodes around it.

    Everything the user already set on their H3 node is kept - model, seed,
    resolution, whatever it has. Only the four inputs a song folder actually
    drives are rewired, and a save prefix is attached at the back.
    """
    g = dict(raw)
    nid = find_h3_in(g, a.h3_class)
    if not nid:
        sys.exit("no H3 node in that workflow. Looked for class %r and for a node "
                 "with both `prompt` and `length`. Is it the API export?" % a.h3_class)

    def free(start):
        n = start
        while str(n) in g:
            n += 1
        return str(n)

    src = free(9000)
    g[src] = {"class_type": "HurricaneSongFolder",
              "_meta": {"title": "SONG - set song_path to this folder on the "
                                 "ComfyUI machine"},
              "inputs": {"song_path": "", "scene_index": 1,
                         "variant": "v1", "out_subfolder": ""}}
    au = free(9001)
    g[au] = {"class_type": a.audio_class, "_meta": {"title": "AUDIO"},
             "inputs": {a.audio_field: [src, song_out("audio_path")]}}

    ins = g[nid].setdefault("inputs", {})
    ins["prompt"] = [src, song_out("prompt")]
    ins["length"] = [src, song_out("frames")]
    a_slot = audio_slot(ins)
    if a_slot:
        ins[a_slot] = [au, 0]

    # The reference sheets are CONSTANT for the whole song - only the prompt, the
    # length and the audio slice change per scene. So the loaders already feeding
    # ref_image_* are correct and are left exactly as they are. They only get
    # retitled with their live tag, so the graph says which image is <Picture 3>.
    slots = image_slots(ins)
    refs = read_refs(song)
    retitled = 0
    for i, slot in enumerate(slots):
        link = ins.get(slot)
        if not (isinstance(link, list) and link[0] in g):
            continue
        if i < len(refs):
            g[link[0]].setdefault("_meta", {})["title"] = refs[i][1]
            retitled += 1

    # a save node the user already has keeps its settings, it only learns where
    saved = [k for k, n in g.items() if "filename_prefix" in n.get("inputs", {})]
    if saved:
        for k in saved:
            g[k]["inputs"]["filename_prefix"] = [src, song_out("save_prefix")]
    else:
        g[free(9200)] = save_node(a, [src, song_out("save_prefix")])

    report = ["node %s (%s) kept its own settings: %s"
              % (nid, g[nid]["class_type"],
                 ", ".join("%s=%r" % (k, v) for k, v in sorted(ins.items())
                           if not isinstance(v, list)) or "none")]
    report.append("rewired: prompt, length, %s"
                  % ("audio -> %s" % a_slot if a_slot else "NO audio slot found"))
    report.append("reference sheets left alone (they are the same in every scene); "
                  "%d loader(s) retitled with their live tag" % retitled)
    connected = sum(1 for k in slots if isinstance(ins.get(k), list))
    if connected < len(refs):
        report.append("! %d sheets in _source/refs but only %d ref_image slot(s) are "
                      "connected. Wire up the rest in ComfyUI and re-wrap, or those "
                      "sheets never reach H3." % (len(refs), connected))
    if any(t in ("CONDITIONING", "LATENT")
           for t in (g[nid].get("_out_types") or ())):
        report.append("that node conditions a sampler rather than returning a "
                      "video; the rest of your chain is untouched")
    report.append("saved via %s, filename_prefix now comes from save_prefix"
                  % (", ".join(sorted(saved)) if saved else "a new SAVE node"))

    g, dropped = prune_unreachable(g)
    if dropped:
        report.append("removed %d node(s) your graph no longer needs, because this "
                      "folder feeds those inputs now:" % len(dropped))
        for nid, cls, title in dropped:
            report.append("    %-5s %-26s %s" % (nid, cls, title))
    return g, report


def wf_upscale(song, a):
    """The pass AFTER rendering, and there is no H3 in it.

    Point Hurricane Clip Folder at the folder you pruned by hand, set clip_index
    to `increment` and the batch count to clip_count, and it walks every clip
    that is still there, in name order. Audio rides through untouched.

    One 4x model, no scaling node after it: the output is exactly what the model
    produces. Whether that lands on 4K depends on what the renders came out at,
    and correcting it is a job for the edit.

    HurricaneClipFolder lives in watching_hurricanes_upscale.py, a separate file
    from the storyboard nodes.
    """
    g = {}
    g["1"] = {"class_type": "HurricaneClipFolder",
              "_meta": {"title": "CLIPS IN - set source_dir"},
              "inputs": {"source_dir": "", "clip_index": 1,
                         "out_subfolder": "%s-2K" % os.path.basename(
                             os.path.abspath(song)),
                         "extensions": "mp4,mov,webm,mkv"}}
    g["10"] = {"class_type": a.video_load, "_meta": {"title": "LOAD CLIP"},
               "inputs": {"video": ["1", 0], "force_rate": 0, "force_size": "Disabled",
                          "frame_load_cap": 0, "skip_first_frames": 0,
                          "select_every_nth": 1}}
    g["20"] = {"class_type": "UpscaleModelLoader",
               "_meta": {"title": "4x ANIME MODEL"},
               "inputs": {"model_name": a.upscale_model}}
    # nothing after the model: whatever it produces is what gets written
    g["21"] = {"class_type": "ImageUpscaleWithModel", "_meta": {"title": "UPSCALE"},
               "inputs": {"upscale_model": ["20", 0], "image": ["10", 0]}}
    g["30"] = {"class_type": a.video_combine, "_meta": {"title": "CLIPS OUT"},
               "inputs": {"images": ["21", 0], "audio": ["10", 2],
                          "filename_prefix": ["1", 1], "frame_rate": 24,
                          "format": "video/h264-mp4", "pix_fmt": "yuv420p",
                          "crf": 12, "save_output": True}}
    return g


# named after the song, so a folder of them stays legible in ComfyUI's workflow
# list: Federphibien.json renders, Federphibien-4x.json upscales
def wf_names(song):
    name = os.path.basename(os.path.abspath(song))
    return {"song": "%s.json" % name, "upscale": "%s-4x.json" % name}


WORKFLOWS = ((None, wf_upscale, "upscale a folder of renders, no H3 in it"),)

# graphs generated before the H3 node's real shape was known. They wired a song
# folder correctly but carried no sampler chain, so they could never run - the
# render workflow now comes from wrapping one that already works.
LEGACY = ("__wf_1_scene.json", "__wf_2_folder.json", "__wf_3_pipeline.json",
          "__wf_5_upscale.json", "__wf_4_wrapped.json", "__workflow_api.json",
          "__workflow_song.json", "__workflow_song_api.json",
          "__workflow_upscale.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("--h3-class", default=H3_CLASS)
    ap.add_argument("--h3-images", type=int, default=H3_IMAGES)
    ap.add_argument("--audio-class", default=AUDIO_CLASS)
    ap.add_argument("--audio-field", default=AUDIO_FIELD)
    ap.add_argument("--image-class", default=IMAGE_CLASS)
    ap.add_argument("--image-field", default=IMAGE_FIELD)
    ap.add_argument("--save-class", default=SAVE_CLASS)
    ap.add_argument("--upscale-model", default=UPSCALE_MODEL)
    ap.add_argument("--video-load", default=VIDEO_LOAD)
    ap.add_argument("--video-combine", default=VIDEO_COMBINE)

    ap.add_argument("--confirmed", action="store_true",
                    help="the class names came from a live /object_info, not a guess")
    ap.add_argument("--from", dest="raw", metavar="RAW.json",
                    help="wrap this graph instead of building one: your own H3 "
                         "ref2vid export, with our nodes put around it")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    song = a.song.rstrip("/")
    if not os.path.isdir(song):
        sys.exit("no such song folder: %s" % song)
    for old in LEGACY:
        if os.path.isfile(os.path.join(song, old)):
            os.remove(os.path.join(song, old))
    if a.raw:
        with open(a.raw, encoding="utf-8") as fh:
            raw = json.load(fh)
        if "nodes" in raw and "last_node_id" in raw:
            # UI format: graft into it and keep the layout, then also emit the
            # API copy that `mvkit queue` needs
            ui, report = wrap_ui(raw, song, a)
            out_ui = os.path.join(song, wf_names(song)["song"])
            with open(out_ui, "w", encoding="utf-8") as fh:
                json.dump(ui, fh, indent=2)
            print("grafted     : %s" % out_ui)
            for line in report:
                print("  %s" % line)
            api = ui_to_api(json.loads(json.dumps(ui)))
            bad = find_abs_paths(api)
            with open(os.path.join(song, wf_names(song)["song"][:-5] + "-api.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(api, fh, indent=2)
            print("  api copy  : %s-api.json (%d nodes)"
                  % (wf_names(song)["song"][:-5], len(api)))
            for nid, k, v in bad:
                print("  ! node %s.%s holds an absolute path (%s) - it came from "
                      "your graph; check it works where ComfyUI runs" % (nid, k, v))
            return
        out = os.path.join(song, wf_names(song)["song"][:-5] + "-api.json")
        g, report = wrap(raw, song, a)
        for nid, k, v in find_abs_paths(g):
            report.append("! node %s.%s still holds an absolute path (%s) - it came "
                          "from your own graph, check it works where ComfyUI runs"
                          % (nid, k, v))
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(g, fh, indent=2)
        print("wrapped     : %s" % out)
        for line in report:
            print("  %s" % line)
        return

    names = wf_names(song)
    for name, fn, what in WORKFLOWS:
        name = names["upscale"]
        g = fn(song, a)
        bad = find_abs_paths(g)
        if bad:
            sys.exit("%s would carry absolute path(s), which are wrong on the "
                     "machine ComfyUI runs on:\n%s"
                     % (name, "\n".join("  node %s.%s = %r" % b for b in bad)))
        with open(os.path.join(song, name), "w", encoding="utf-8") as fh:
            json.dump(g, fh, indent=2)
    if not a.quiet:
        print("workflows   : %s" % names["upscale"])
        if not os.path.isfile(os.path.join(song, names["song"])):
            print("              no render graph yet - wrap yours:")
            print("              ./mvkit workflows %s --from <your workflow.json>"
                  % os.path.basename(os.path.abspath(song)))


if __name__ == "__main__":
    main()

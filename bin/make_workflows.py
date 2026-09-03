#!/usr/bin/env python3
"""Write the ComfyUI workflows into a song folder.

  make_workflows.py <song-dir> [--from your_workflow.json]

  __workflow_upscale.json  the pass after rendering: a folder of clips through a
                           4x line-art model. Complete and standalone.
  __workflow_song.json     written by --from: YOUR H3 graph with a song folder
                           wired into it. The render workflow.

The H3 node returns `positive` and `LATENT`, not a video, so there is no point
generating a render graph from scratch - the model, sampler and settings cannot be
guessed. Hand it one that works instead:

    make_workflows.py <song-dir> --from your_workflow.json

That must be a workflow SAVED from the ComfyUI menu, not an API export: the graft
edits the saved format in place so the layout and the groups survive, and the
saved format is the one you open again to render.

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
# One 4x line-art model, and whatever it produces is what gets written. No
# rescaling in the graph: hitting 4K exactly is the edit's job.
UPSCALE_MODEL = "RealESRGAN_x4plus_anime_6B.pth"
VIDEO_LOAD = "VHS_LoadVideoPath"
VIDEO_COMBINE = "VHS_VideoCombine"
# Not a placeholder any more - the class name is confirmed. What IS incomplete is
# the graph: this node returns positive/LATENT, so a model loader, a sampler, a
# VAE decode and a video output have to come from somewhere, and none of them can
# be guessed. `--from your_export.json` keeps yours.
NOTE = ("this node conditions a sampler - it returns positive/LATENT, not a "
        "video. Attach your own model/sampler/VAEDecode chain, or better: "
        "`mvkit workflows <song> --from your_saved_workflow.json`")


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
        # ("refs/01_....png"), so joining the refs dir again doubles it
        rel = i.get("file", "")
        out.append((i.get("tag", ""),
                    "%s %s (%s)" % (i.get("tag", ""), i.get("slug", ""),
                                    i.get("kind", "")),
                    rel, os.path.basename(rel)))
    return out


def read_sets(song):
    """-> [(folder, [sheet numbers], scene count)] for the per-set folders.

    Each of those folders is a song folder whose scenes all need the same sheets,
    which is what lets a graph carry only those sheets and wire them in one fixed
    order."""
    out = []
    for d in sorted(os.listdir(song)):
        if not (d.startswith("set-") and os.path.isdir(os.path.join(song, d))):
            continue
        man = os.path.join(song, d, "__SCENES.tsv")
        if not os.path.isfile(man):
            continue
        with open(man, encoding="utf-8") as fh:
            rows = [l.rstrip("\n").split("\t") for l in fh if l.strip()]
        col = rows[0].index("refs")
        sheets = [[int(x) for x in re.split(r"[^0-9]+", r[col]) if x]
                  for r in rows[1:]]
        if not sheets or any(x != sheets[0] for x in sheets):
            sys.exit("%s/__SCENES.tsv does not name one set of sheets for all its "
                     "scenes - re-run `mvkit build`" % d)
        out.append((d, sheets[0], len(sheets)))
    if not out:
        sys.exit("%s holds no set-* folder - run `mvkit build` first" % song)
    return out


OUTPUT_CLASSES = re.compile(r"^(Save|Preview|VHS_VideoCombine|SaveAudio|SaveVideo)",
                            re.I)

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
    "widgets_values": ["", 1, "increment", "v1", ""],
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

# UI-only inputs: they exist so the browser can draw an upload button and are not
# part of what /prompt accepts
UI_ONLY = ("IMAGEUPLOAD", "AUDIOUPLOAD", "AUDIO_UI", "VIDEOUPLOAD")

# A `control_after_generate` widget takes a slot in `widgets_values` but is not
# listed in `inputs` - it is the browser's own counter, not a node input. It only
# ever follows a numeric widget, so skipping it keeps the positional walk aligned.
# Without this, KSampler's seed control shifts steps/cfg/sampler by one.
CONTROL_VALUES = ("fixed", "increment", "decrement", "randomize")


def wrap_ui(ui, song, a, sheets=None, label=""):
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

    def feed(name):
        """-> (link id, source node id, source socket) for one H3 input"""
        for i in (h3.get("inputs") or []):
            if i.get("name") == name and i.get("link") in links:
                l = links[i["link"]]
                return l[0], l[1], l[2]
        return None

    def feeder(name):
        f = feed(name)
        return f[1] if f else None

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
    song_n["title"] = ("WATCHING HURRICANES - %s" % label if label else
                       "WATCHING HURRICANES - Song Folder (set song_path)")
    song_n["widgets_values"][4] = os.path.basename(os.path.abspath(song))
    aud_n = place("VHS_LoadAudio", where(feeder(a_slot)) if a_slot else [0, 0])
    aud_n["title"] = "AUDIO - this scene's slice"

    def out_index(n, name):
        for k, o in enumerate(n.get("outputs") or []):
            if o.get("name") == name:
                return k
        sys.exit("node %s has no output named %r - the socket definition and the "
                 "node have drifted apart" % (n.get("type"), name))

    def connect(src, sname, dst, dname, typ):
        wire(src, out_index(src, sname), dst, dname, typ)

    def wire(src, si, dst, dname, typ):
        nonlocal lid
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

    # The sheets stop feeding H3 directly. A picture H3 can see is a picture H3
    # uses - the prompt cannot talk it out of one - so the router hands each
    # scene only the sheets it contains, in the order the prompt numbers them.
    refs = read_refs(song)
    slots = image_slots({i["name"]: 1 for i in (h3.get("inputs") or [])})
    wired = [(slot, f) for slot, f in ((s_, feed(s_)) for s_ in slots)
             if f and f[1] in nodes]
    # sheet n is whatever feeds H3's nth image slot in the graph you saved, so the
    # loaders have to be connected in the order __READ_ME.txt lists the sheets
    if sheets is None:
        # every sheet on every scene, straight into H3: the wiring as it was
        for k, (slot, f) in enumerate(wired):
            if k < len(refs):
                nodes[f[1]]["title"] = refs[k][1]
        kept, dropped = wired, []
    else:
        if max(sheets) > len(wired):
            sys.exit("this set needs sheet %d, but only %d of H3's ref_image slots "
                     "have an image connected in %s.\nConnect them all in ComfyUI, "
                     "save the workflow again, and re-run this."
                     % (max(sheets), len(wired), os.path.basename(a.raw)))
        kept = [wired[n - 1] for n in sheets]
        dropped = [w for w in wired if w not in kept]
        stale = {f[0] for slot, f in wired}
        for k, (slot, f) in enumerate(kept):
            wire(nodes[f[1]], f[2], h3, slots[k], "IMAGE")
            what = (refs[sheets[k] - 1][1].split("> ", 1)[-1]
                    if sheets[k] <= len(refs) else "")
            nodes[f[1]]["title"] = ("<Picture %d> - %s  [sheet %d]"
                                    % (k + 1, what, sheets[k]))
        # every slot past this set stays empty, and the loaders behind them go:
        # a sheet H3 can see is a sheet H3 uses, whatever the prompt says
        for slot in slots[len(kept):]:
            for i in (h3.get("inputs") or []):
                if i.get("name") == slot:
                    i.pop("link", None)
        ui["links"] = [l for l in ui["links"] if l[0] not in stale]
        for n in ui["nodes"]:
            for o in (n.get("outputs") or []):
                o["links"] = [x for x in (o.get("links") or []) if x not in stale]
        gone = {f[1] for slot, f in dropped
                if not any(o.get("links") for o in (nodes[f[1]].get("outputs") or []))}
        displaced |= gone

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

    report = ["%d node(s) gone - the prompt, length and audio feeders, plus the "
              "sheet loaders this graph does not use: %s"
              % (len(displaced), ", ".join("%s %s" % (i, nodes[i].get("type"))
                                           for i in sorted(displaced) if i in nodes)),
              ("%d sheet(s) wired as <Picture 1..%d>, %d loader(s) removed, "
               "%d of H3's %d image slot(s) left empty"
               % (len(kept), len(kept), len(dropped), len(slots) - len(kept),
                  len(slots)))
              if sheets is not None else
              ("all %d reference sheet(s) left as they were, retitled with their "
               "tag" % len(wired)),
              "save prefix driven on %d node(s)" % len(saves),
              "layout and %d group(s) kept" % len(ui.get("groups") or [])]
    return ui, report


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
              "_meta": {"title": "WATCHING HURRICANES - Clip Folder "
                                 "(set source_dir)"},
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
    return {"song": "%s.json" % name, "upscale": "%s-4x.json" % name,
            "allsheets": "%s-allsheets.json" % name}


def set_graph_name(song, folder):
    return "%s-%s.json" % (os.path.basename(os.path.abspath(song)), folder)


WORKFLOWS = ((None, wf_upscale, "upscale a folder of renders, no H3 in it"),)

# graphs generated before the H3 node's real shape was known. They wired a song
# folder correctly but carried no sampler chain, so they could never run - the
# render workflow now comes from grafting into one that already works. The
# -api copies went with the HTTP queue; the graph you open is the saved format.
LEGACY = ("__wf_1_scene.json", "__wf_2_folder.json", "__wf_3_pipeline.json",
          "__wf_5_upscale.json", "__wf_4_wrapped.json", "__workflow_api.json",
          "__workflow_song.json", "__workflow_song_api.json",
          "__workflow_upscale.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("--h3-class", default=H3_CLASS)
    ap.add_argument("--upscale-model", default=UPSCALE_MODEL)
    ap.add_argument("--video-load", default=VIDEO_LOAD)
    ap.add_argument("--video-combine", default=VIDEO_COMBINE)

    ap.add_argument("--from", dest="raw", metavar="RAW.json",
                    help="graft the song folder into this saved workflow instead "
                         "of building one - your own H3 ref2vid graph, layout kept")
    ap.add_argument("--all-sheets", action="store_true",
                    help="graft the pre-refsets wiring instead: every sheet on "
                         "every scene. Needs `mvkit build --all-sheets` prompts.")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    song = a.song.rstrip("/")
    if not os.path.isdir(song):
        sys.exit("no such song folder: %s" % song)
    # the whole-song graph is gone: refsets/ holds one graph per set instead.
    # -allsheets.json is not swept up - it is the pre-refsets wiring, on request.
    for old in LEGACY + (wf_names(song)["song"],
                         wf_names(song)["song"][:-5] + "-api.json"):
        if os.path.isfile(os.path.join(song, old)):
            os.remove(os.path.join(song, old))
    # the graph you grafted from is kept, so a rebuild can re-graft on its own -
    # `mvkit build` wipes refsets/ and everything in it, the set graphs included
    kept = os.path.join(song, "_source", "workflow.json")
    raw = None
    if a.raw:
        with open(a.raw, encoding="utf-8") as fh:
            raw = json.load(fh)
        if "nodes" not in raw or "last_node_id" not in raw:
            sys.exit("that is not a saved workflow. In ComfyUI use Workflow -> Save "
                     "(or Export),\nnot Export (API): the API format carries no "
                     "layout and no groups and\ncannot be opened in the editor.")
        if os.path.abspath(a.raw) != os.path.abspath(kept):
            with open(kept, "w", encoding="utf-8") as fh:
                json.dump(raw, fh, indent=2)
            print("kept        : _source/workflow.json - every build re-grafts the "
                  "set graphs from it")
    elif os.path.isfile(kept):
        with open(kept, encoding="utf-8") as fh:
            raw = json.load(fh)
    if raw is not None:
        if a.all_sheets:
            # the wiring as it was before the per-set graphs: every sheet on every
            # scene. Only renderable against `mvkit build --all-sheets` prompts,
            # which number every sheet of the song instead of the set's own.
            ui, report = wrap_ui(raw, song, a)
            out_ui = os.path.join(song, wf_names(song)["allsheets"])
            with open(out_ui, "w", encoding="utf-8") as fh:
                json.dump(ui, fh, indent=2)
            print("grafted     : %s   (needs `mvkit build --all-sheets`)" % out_ui)
            for line in report:
                print("  %s" % line)
            return
        # one graph per reference set, in that set's own folder: it carries only
        # the sheets those scenes contain, in the order their prompts number them
        sets = read_sets(song)
        refs = read_refs(song)
        for folder, sheets, scenes in sets:
            # what the set holds, in words: the graph says which pictures it
            # loads, this says whose they are and how many scenes use them
            who = ", ".join(refs[n - 1][1].split("> ", 1)[-1].split(" (")[0]
                            for n in sheets if n <= len(refs))
            label = ("%s: %s | %d scene(s) | point song_path here"
                     % (folder, who, scenes))
            ui, report = wrap_ui(json.loads(json.dumps(raw)), song, a, sheets,
                                 label)
            out_ui = os.path.join(song, folder, set_graph_name(song, folder))
            with open(out_ui, "w", encoding="utf-8") as fh:
                json.dump(ui, fh, indent=2)
            if a.raw:
                print("grafted     : %s/%s" % (folder,
                                                   os.path.basename(out_ui)))
                print("  %s" % report[1])
        if a.raw:
            print("each graph  : %s" % report[0])
            print("              %s, %s" % (report[2], report[3]))
        else:
            print("set graphs  : %d, re-grafted from _source/workflow.json"
                  % len(sets))

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
        if raw is None:
            print("              no set graphs yet - graft yours once:")
            print("              ./mvkit workflows %s --from <your workflow.json>"
                  % os.path.basename(os.path.abspath(song)))


if __name__ == "__main__":
    main()

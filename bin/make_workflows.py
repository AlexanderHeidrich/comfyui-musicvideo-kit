#!/usr/bin/env python3
"""Write the three starting ComfyUI workflows into a song folder.

  make_workflows.py <song-dir> [--h3-class NAME] [--h3-images N]
                    [--audio-class NAME] [--image-class NAME] [--save-class NAME]

  __wf_1_scene.json     one scene, everything explicit. Each reference loader is
                        titled with its live tag, so you can see which image is
                        <Picture 3> without opening refs.json. Driven from
                        outside with `mvkit queue`.
  __wf_2_folder.json    Hurricane Song Folder drives the whole song from this folder.
  __wf_3_pipeline.json  Hurricane Build Song runs ./mvkit first, then the same.

The H3 node's class name and how many image inputs it has cannot be known
without a running ComfyUI, so they default to the names below and `mvkit probe`
rewrites all three with what your server actually reports. Until then ComfyUI may
show the H3 node as missing - that is the placeholder, not a broken graph.

Stdlib only.
"""
import argparse
import json
import os
import sys

H3_CLASS = "MiniMaxHailuoH3Ref2VideoAudio"
H3_IMAGES = 9
AUDIO_CLASS = "VHS_LoadAudio"
AUDIO_FIELD = "audio_file"
IMAGE_CLASS = "VHS_LoadImagePath"
IMAGE_FIELD = "path"
SAVE_CLASS = "SaveVideo"
NOTE = ("placeholder class name - run `mvkit probe --song <name> --emit` against a "
        "running ComfyUI to replace it with the real one")


def read_refs(song):
    """-> [(tag, label, abs path)] for the reference sheets, in slot order"""
    rj = os.path.join(song, "_source", "refs.json")
    if not os.path.isfile(rj):
        return []
    with open(rj, encoding="utf-8") as fh:
        data = json.load(fh)
    rdir = os.path.join(song, "_source", "refs")
    out = []
    for i in data.get("images", []):
        out.append((i.get("tag", ""),
                    "%s %s (%s)" % (i.get("tag", ""), i.get("slug", ""),
                                    i.get("kind", "")),
                    os.path.abspath(os.path.join(rdir, i.get("file", "")))))
    return out


def first_scene(song):
    """-> (prompt path, audio path, frames) for the first scene with audio"""
    man = os.path.join(song, "__SCENES.tsv")
    if not os.path.isfile(man):
        return None, None, 124
    with open(man, encoding="utf-8") as fh:
        rows = [l.rstrip("\n").split("\t") for l in fh if l.strip()]
    head = rows[0]
    for r in rows[1:]:
        d = dict(zip(head, r))
        audio = (d.get("audio") or "-").strip()
        pf = [f for f in (d.get("prompts") or "").split() if f.endswith("-v1.txt")]
        if audio not in ("", "-") and pf:
            return (os.path.abspath(os.path.join(song, pf[0])),
                    os.path.abspath(os.path.join(song, audio)),
                    int(d.get("frames") or 124))
    return None, None, 124


def h3_node(a, extra_inputs, title):
    inputs = {"prompt": "", "length": 124}
    inputs.update(extra_inputs)
    meta = {"title": title}
    if not a.confirmed:
        meta["note"] = NOTE
    return {"class_type": a.h3_class, "inputs": inputs, "_meta": meta}


def save_node(a, src, prefix):
    """prefix may be a literal or a link. Without it ComfyUI names every clip
    after the node default and they all land in one heap in output/."""
    return {"class_type": a.save_class,
            "inputs": {"video": [src, 0], "filename_prefix": prefix},
            "_meta": {"title": "SAVE"}}


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
    g[src] = {"class_type": "HurricaneSongFolder", "_meta": {"title": "SONG"},
              "inputs": {"song_path": os.path.abspath(song), "scene_index": 1,
                         "variant": "v1", "out_subfolder": ""}}
    au = free(9001)
    g[au] = {"class_type": a.audio_class, "_meta": {"title": "AUDIO"},
             "inputs": {a.audio_field: [src, 1]}}

    ins = g[nid].setdefault("inputs", {})
    ins["prompt"] = [src, 0]
    ins["length"] = [src, 2]
    for k, v in list(ins.items()):
        if k.startswith("audio"):
            ins[k] = [au, 0]

    # the reference sheets, into whatever image slots this node has
    slots = sorted(k for k in ins if k.startswith("image"))
    refs = read_refs(song)[:len(slots) or a.h3_images]
    for i, (tag, label, _) in enumerate(refs):
        if i >= len(slots):
            break
        img = free(9100 + i)
        g[img] = {"class_type": a.image_class, "_meta": {"title": label},
                  "inputs": {a.image_field: [src, 6 + i]}}
        ins[slots[i]] = [img, 0]

    # a save node the user already has keeps its settings, it only learns where
    saved = [k for k, n in g.items() if "filename_prefix" in n.get("inputs", {})]
    if saved:
        for k in saved:
            g[k]["inputs"]["filename_prefix"] = [src, 15]
    else:
        g[free(9200)] = save_node(a, nid, [src, 15])

    report = ["node %s (%s) kept its own settings: %s"
              % (nid, g[nid]["class_type"],
                 ", ".join("%s=%r" % (k, v) for k, v in sorted(ins.items())
                           if not isinstance(v, list)) or "none")]
    report.append("rewired: prompt, length, %d audio, %d of %d image slot(s)"
                  % (sum(1 for k in ins if k.startswith("audio")),
                     min(len(refs), len(slots)), len(slots)))
    if len(read_refs(song)) > len(slots):
        report.append("! %d reference sheets but only %d image slot(s) on that node - "
                      "%d dropped. Add image inputs in ComfyUI and re-wrap."
                      % (len(read_refs(song)), len(slots),
                         len(read_refs(song)) - len(slots)))
    orphans = [k for k, n in g.items()
               if k not in (src, au) and not k.startswith("91")
               and n.get("class_type") in (a.audio_class, IMAGE_CLASS, "LoadImage",
                                           "LoadAudio", "LoadImageFromPath")]
    if orphans:
        report.append("your own loader node(s) %s are now unreachable - harmless, "
                      "delete them if you like" % ", ".join(sorted(orphans)))
    report.append("saved via %s, filename_prefix now comes from save_prefix"
                  % (", ".join(sorted(saved)) if saved else "a new SAVE node"))
    return g, report


def wf_scene(song, a):
    """one scene, every file named and pre-filled"""
    prompt_f, audio_f, frames = first_scene(song)
    refs = read_refs(song)[:a.h3_images]
    g = {}
    g["10"] = {"class_type": a.audio_class, "_meta": {"title": "AUDIO"},
               "inputs": {a.audio_field: audio_f or ""}}
    h3_extra = {"length": frames, "audio1": ["10", 0]}
    for n, (tag, label, path) in enumerate(refs, 1):
        nid = str(100 + n)
        # the title IS the live tag, so the graph says which image is which
        g[nid] = {"class_type": a.image_class, "_meta": {"title": label},
                  "inputs": {a.image_field: path}}
        h3_extra["image%d" % n] = [nid, 0]
    if prompt_f:
        with open(prompt_f, encoding="utf-8") as fh:
            h3_extra["prompt"] = fh.read()
    g["20"] = h3_node(a, h3_extra, "PROMPT")
    g["30"] = save_node(a, "20", "%s/scene" % os.path.basename(os.path.abspath(song)))
    return g


def wf_folder(song, a):
    """Hurricane Song Folder drives the lot"""
    refs = read_refs(song)[:a.h3_images]
    g = {"1": {"class_type": "HurricaneSongFolder", "_meta": {"title": "SONG"},
               "inputs": {"song_path": os.path.abspath(song),
                          "scene_index": 1, "variant": "v1"}}}
    g["10"] = {"class_type": a.audio_class, "_meta": {"title": "AUDIO"},
               "inputs": {a.audio_field: ["1", 1]}}
    h3_extra = {"prompt": ["1", 0], "length": ["1", 2], "audio1": ["10", 0]}
    for n, (tag, label, _) in enumerate(refs, 1):
        nid = str(100 + n)
        g[nid] = {"class_type": a.image_class, "_meta": {"title": label},
                  "inputs": {a.image_field: ["1", 5 + n]}}   # ref_1 is output 6
        h3_extra["image%d" % n] = [nid, 0]
    g["20"] = h3_node(a, h3_extra, a.h3_class)
    g["30"] = save_node(a, "20", ["1", 15])
    return g


def wf_pipeline(song, a):
    """Hurricane Build Song: run the kit on the host first"""
    kit = os.path.abspath(os.path.join(song, "..", ".."))
    g = {"1": {"class_type": "HurricaneBuildSong", "_meta": {"title": "BUILD"},
               "inputs": {"kit_path": kit,
                          "song_name": os.path.basename(os.path.abspath(song)),
                          "scene_index": 1, "variant": "v1",
                          "stage": "build only"}}}
    g["10"] = {"class_type": a.audio_class, "_meta": {"title": "AUDIO"},
               "inputs": {a.audio_field: ["1", 1]}}
    g["20"] = h3_node(a, {"prompt": ["1", 0], "length": ["1", 2],
                          "audio1": ["10", 0]}, a.h3_class)
    g["30"] = save_node(a, "20", ["1", 5])
    g["40"] = {"class_type": "PreviewAny", "_meta": {"title": "KIT LOG"},
               "inputs": {"source": ["1", 6]}}
    return g


WORKFLOWS = (("__wf_1_scene.json", wf_scene, "one scene, every file named"),
             ("__wf_2_folder.json", wf_folder, "the folder node drives the song"),
             ("__wf_3_pipeline.json", wf_pipeline, "run the kit, then the song"))


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
    if a.raw:
        with open(a.raw, encoding="utf-8") as fh:
            raw = json.load(fh)
        if "nodes" in raw and "last_node_id" in raw:
            sys.exit("that is a UI workflow. In ComfyUI: Workflow -> Export (API).")
        out = os.path.join(song, "__wf_4_wrapped.json")
        g, report = wrap(raw, song, a)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(g, fh, indent=2)
        print("wrapped     : %s" % out)
        for line in report:
            print("  %s" % line)
        return

    for name, fn, what in WORKFLOWS:
        with open(os.path.join(song, name), "w", encoding="utf-8") as fh:
            json.dump(fn(song, a), fh, indent=2)
    if not a.quiet:
        print("workflows   : %s%s"
              % (", ".join(n for n, _, _ in WORKFLOWS),
                 "" if a.confirmed else "  (H3 class is a guess until `mvkit probe`)"))


if __name__ == "__main__":
    main()

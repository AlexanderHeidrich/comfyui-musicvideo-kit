#!/usr/bin/env python3
"""Ask a running ComfyUI what it actually has, and print how to wire a song folder.

  comfy_probe.py [--host http://127.0.0.1:8188] [--object-info saved.json]

ComfyUI serves /object_info: every installed node with its input names and types.
That is the only honest answer to "which nodes do I pick" - node packs rename
things between versions, so this reads the live server instead of guessing.

Stdlib only. env: COMFY_HOST
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_workflows import song_node_outputs  # noqa: E402

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")

# candidates for the parts core ComfyUI cannot do, best first. No audio loader
# among them: H3 gets no audio reference, the song goes under the picture later.
INT_PRIMITIVE = ("PrimitiveInt", "INTConstant", "Int", "PrimitiveNode")
# only these take a path; core LoadImage is a dropdown over ComfyUI/input
IMAGE_LOADER = ("LoadImageFromPath", "VHS_LoadImagePath", "Image Load")
VIDEO_SAVE = ("SaveVideo", "VHS_VideoCombine", "SaveAnimatedWEBP")


def fetch(host, path, timeout=20):
    url = host.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit("ComfyUI answered %s for %s" % (e.code, url))
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit("cannot reach ComfyUI at %s (%s).\nIs it running? Set --host or "
                 "COMFY_HOST if it is on another port or machine." % (host, e))


def widgets(spec):
    """-> {name: type} for the inputs a queue run can set, i.e. not links.

    An input is settable when its declared type is a primitive name (STRING,
    INT, FLOAT, BOOLEAN) or a list of choices; anything else arrives over a wire.
    """
    out = {}
    for group in ("required", "optional"):
        for name, decl in (spec.get("input", {}).get(group) or {}).items():
            t = decl[0] if isinstance(decl, (list, tuple)) and decl else decl
            if isinstance(t, list):
                out[name] = "COMBO[%d]" % len(t)
            elif t in ("STRING", "INT", "FLOAT", "BOOLEAN"):
                out[name] = t
    return out


def links(spec):
    out = {}
    for group in ("required", "optional"):
        for name, decl in (spec.get("input", {}).get(group) or {}).items():
            t = decl[0] if isinstance(decl, (list, tuple)) and decl else decl
            if isinstance(t, str) and t not in ("STRING", "INT", "FLOAT", "BOOLEAN"):
                out[name] = t
    return out


def find_h3(info):
    """the MiniMax H3 node, by class name or by category"""
    hits = []
    for cls, spec in info.items():
        blob = "%s %s %s" % (cls, spec.get("category", ""), spec.get("display_name", ""))
        if re.search(r"minimax|(?<![a-z0-9])h3(?![a-z0-9])", blob, re.I):
            hits.append((cls, spec))
    # ref2v first: it is the one that takes references AND a prompt
    hits.sort(key=lambda x: (0 if re.search(r"ref", x[0], re.I) else 1, x[0]))
    return hits


def first_present(info, names):
    for n in names:
        if n in info:
            return n
    return None


def report(info, host):
    print("ComfyUI at %s: %d node types installed" % (host, len(info)))
    print()

    h3 = find_h3(info)
    if not h3:
        print("! no MiniMax H3 node found.")
        print("  Nothing matched 'minimax' or 'h3' in a class name, display name")
        print("  or category. Update ComfyUI - ref2v ships in comfy_extras.")
    else:
        print("MiniMax H3 nodes found:")
        for cls, _ in h3:
            print("  %s" % cls)
        print()
        cls, spec = h3[0]
        w, l = widgets(spec), links(spec)
        print("Using %s. Its settable fields:" % cls)
        for n, t in sorted(w.items()):
            print("    %-22s %s" % (n, t))
        print("  and its wired inputs:")
        for n, t in sorted(l.items()):
            print("    %-22s %s" % (n, t))
        outs = list(spec.get("output") or ())
        names = list(spec.get("output_name") or ())
        print("  what it RETURNS:")
        for i, t in enumerate(outs):
            print("    %-22s %s" % (names[i] if i < len(names) else "out %d" % i, t))
        if any(t in ("CONDITIONING", "LATENT") for t in outs):
            print()
            print("  This node CONDITIONS A SAMPLER - it does not hand back a video.")
            print("  A finished graph therefore needs the rest of a local pipeline")
            print("  (model loader, sampler, VAE decode, video combine), none of")
            print("  which can be guessed from here. Build that chain once in the UI,")
            print("  export it, and wrap it:")
            print("      ./mvkit workflows <song> --from your_export.json")
        print()
    print("The parts core ComfyUI cannot do:")
    for what, names, why in (
            ("settable int", INT_PRIMITIVE, "to drive `length` per scene"),
            ("image by path", IMAGE_LOADER, "for the reference sheets"),
            ("write the clip", VIDEO_SAVE, "to get a file out")):
        got = first_present(info, names)
        print("  %-14s %s" % (what, got if got else "MISSING - %s" % why))
        if not got:
            print("  %-14s   install one of: %s" % ("", ", ".join(names)))
    print()
    print("Ours, from comfyui/custom_nodes/:")
    for f, classes in (("watching_hurricanes.py", ("HurricaneSongFolder",)),
                       ("watching_hurricanes_upscale.py",
                        ("HurricaneClipFolder",))):
        print("  %s" % f)
        for cls in classes:
            print("    %-28s %s" % (cls, "yes" if cls in info else "not loaded"))
    if "HurricaneSongFolder" not in info:
        print("  HurricaneSongFolder is the one that matters: it turns a song")
        print("  folder into a batch. Copy comfyui/custom_nodes/watching_hurricanes.py")
        print("  into your ComfyUI/custom_nodes/ and restart.")
    else:
        stale_song_node(info["HurricaneSongFolder"])


def stale_song_node(spec):
    """Does the loaded node have the sockets the graphs were wired against?

    Graphs wire outputs by index, so an older copy in custom_nodes/ shifts every
    link past the change: `length` fed a STRING ("incompatible input and output
    types"), `filename_prefix` fed scene_count.
    """
    live = list(zip(spec.get("output_name") or (), spec.get("output") or ()))
    ours = song_node_outputs()
    if live == ours:
        return
    print("  ! the loaded copy is not this kit's:")
    print("      loaded: %s" % ", ".join("%s:%s" % o for o in live))
    print("      ours  : %s" % ", ".join("%s:%s" % o for o in ours))
    print("    Every set graph wires these by index, so a graph opened against")
    print("    that copy lands on the wrong sockets. Copy")
    print("    comfyui/custom_nodes/watching_hurricanes.py into your")
    print("    ComfyUI/custom_nodes/ and restart ComfyUI.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--object-info", help="read a saved /object_info dump instead")
    a = ap.parse_args()

    if a.object_info:
        with open(a.object_info, encoding="utf-8") as fh:
            info = json.load(fh)
        print("read %d node types from %s" % (len(info), a.object_info))
        print()
    else:
        info = fetch(a.host, "/object_info")
    report(info, a.object_info or a.host)


if __name__ == "__main__":
    main()

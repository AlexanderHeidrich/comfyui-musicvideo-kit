#!/usr/bin/env python3
"""Ask a running ComfyUI what it actually has, and print how to wire a song folder.

  comfy_probe.py [--host http://127.0.0.1:8188] [--object-info saved.json]
                 [--emit workflow_api.json] [--song songs/NAME]

ComfyUI serves /object_info: every installed node with its input names and types.
That is the only honest answer to "which nodes do I pick" - node packs rename
things between versions, so this reads the live server instead of guessing.

--emit writes a starting API-format graph with the nodes it found, already titled
for `mvkit queue`. Open it in ComfyUI and check it before trusting it.

Stdlib only. env: COMFY_HOST
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")

# what a song folder needs driven, and the input names each role can live in
ROLES = (
    ("PROMPT", ("prompt", "text", "string", "value")),
    ("AUDIO", ("audio", "audio_file", "path", "file", "value")),
    ("LENGTH", ("length", "frames", "value", "int")),
)

# candidates for the parts core ComfyUI cannot do, best first
AUDIO_BY_PATH = ("VHS_LoadAudio", "VHS_LoadAudioUpload", "LoadAudioPath",
                 "Load Audio (Path)", "WAS_Load_Audio")
INT_PRIMITIVE = ("PrimitiveInt", "INTConstant", "Int", "PrimitiveNode")
IMAGE_LOADER = ("LoadImage", "LoadImageFromPath", "VHS_LoadImagePath")
# only these take a path; core LoadImage is a dropdown over ComfyUI/input
IMAGE_BY_PATH = ("LoadImageFromPath", "VHS_LoadImagePath", "Image Load")
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
        # A node carries ONE title, so two roles that both live on the H3 node
        # cannot both be titled. Either title it once and point both roles at that
        # title, or give the second role its own upstream node.
        on_h3 = [r for r, keys in ROLES if any(k in w for k in keys)]
        print("Wiring plan for `mvkit queue`:")
        if len(on_h3) > 1:
            print("    %s are all settable on %s itself, and a node has only one"
                  % (" and ".join(on_h3), cls))
            print("    title. Two ways round it, both fine:")
            print()
            print("    a) title the H3 node `H3` and point the roles at that title:")
            print("         ./mvkit queue <song> wf.json \\")
            print("             %s" % " \\\n             ".join(
                "--title-%s H3" % r.lower() for r in on_h3))
            print("       queue picks a different field per role on the same node.")
            print()
            print("    b) or keep one role on the H3 node and feed the other from its")
            print("       own upstream node titled after that role - which is what")
            print("       --emit writes: LENGTH on its own Int, wired into `length`.")
        elif on_h3:
            print("    %-7s -> title the H3 node '%s'" % (on_h3[0], on_h3[0]))
        for role, keys in ROLES:
            if role in on_h3:
                continue
            over = next((k for k in keys if k in l), None)
            if not over and role == "AUDIO":
                # the real node calls it ref_audio_0. ref_video_audio_* is the
                # soundtrack OF a reference video and is a different thing.
                # by TYPE, not by name: audio_vae is a VAE, and
                # ref_video_audio_* is the soundtrack of a reference video
                cands = [k for k, t in l.items()
                         if t == "AUDIO" and "video" not in k.lower()]
                over = sorted(cands)[0] if cands else None
            if over:
                print("    %-7s -> arrives over a wire (`%s: %s`). Title the node that"
                      % (role, over, l[over]))
                feeder = first_present(info, AUDIO_BY_PATH) if l[over] == "AUDIO" else None
                print("               feeds it '%s'%s"
                      % (role, " - use %s" % feeder if feeder else ""))
            else:
                print("    %-7s -> not on this node at all" % role)
        print()

    print("The parts core ComfyUI cannot do:")
    for what, names, why in (
            ("audio by path", AUDIO_BY_PATH,
             "core LoadAudio only lists files in ComfyUI/input, as a dropdown"),
            ("settable int", INT_PRIMITIVE, "to drive `length` per scene"),
            ("image by path", IMAGE_LOADER, "for the reference sheets"),
            ("write the clip", VIDEO_SAVE, "to get a file out")):
        got = first_present(info, names)
        print("  %-14s %s" % (what, got if got else "MISSING - %s" % why))
        if not got:
            print("  %-14s   install one of: %s" % ("", ", ".join(names)))
    print()
    print("Ours, from comfyui/custom_nodes/:")
    for f, classes in (("watching_hurricanes.py",
                        ("HurricaneSongFolder", "HurricaneBuildSong",
                         "HurricaneStoryboardScene", "HurricaneReferenceInventory",
                         "HurricanePromptBuilder")),
                       ("watching_hurricanes_upscale.py",
                        ("HurricaneClipFolder",))):
        print("  %s" % f)
        for cls in classes:
            print("    %-28s %s" % (cls, "yes" if cls in info else "not loaded"))
    if "HurricaneSongFolder" not in info:
        print("  HurricaneSongFolder is the one that matters: it turns a song")
        print("  folder into a batch. Copy comfyui/custom_nodes/watching_hurricanes.py")
        print("  into your ComfyUI/custom_nodes/ and restart.")


def emit(info, path, song):
    """Regenerate the song's three workflows with what this server really has."""
    import subprocess
    h3 = find_h3(info)
    if not h3:
        sys.exit("cannot write workflows without an H3 node - see the report above")
    cls, spec = h3[0]
    l = links(spec)
    n_img = sum(1 for t in l.values() if t == "IMAGE")
    audio_cls = first_present(info, AUDIO_BY_PATH)
    image_cls = first_present(info, IMAGE_BY_PATH)
    save_cls = first_present(info, VIDEO_SAVE)
    if not audio_cls:
        sys.exit("no node that loads audio by path - install ComfyUI-VideoHelperSuite")
    if not image_cls:
        print("! nothing loads an image BY PATH; the reference loaders will be")
        print("  written as %s anyway - install one of: %s"
              % (IMAGE_BY_PATH[0], ", ".join(IMAGE_BY_PATH)))
        image_cls = IMAGE_BY_PATH[0]

    def field(cls_name, names, default):
        w = widgets(info.get(cls_name, {}))
        return next((k for k in names if k in w), default)

    cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "make_workflows.py"), song,
           "--h3-class", cls, "--h3-images", str(n_img or 9),
           "--audio-class", audio_cls,
           "--audio-field", field(audio_cls, ("path", "audio_file", "file"), "path"),
           "--image-class", image_cls,
           "--image-field", field(image_cls, ("path", "image_path", "file"), "path"),
           "--save-class", save_cls or "SaveVideo", "--confirmed"]
    print()
    print("H3 node        : %s  (%d image inputs)" % (cls, n_img))
    subprocess.run(cmd, check=True)
    print("  Written into %s. They are STARTING points: the H3 node's own settings"
          % song)
    print("  are blank and nothing about your model or account is guessed. Open one,")
    print("  finish it, render ONE scene, then Export (API) over it.")
    print("  __wf_2_folder.json is the one you want: set SONG.scene_index to")
    print("  `increment` and the queue's batch count to scene_count, then Run.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--object-info", help="read a saved /object_info dump instead")
    ap.add_argument("--emit", action="store_true",
                    help="rewrite the song's three workflows with the classes this "
                         "server actually reports")
    ap.add_argument("--song", help="song folder the workflow belongs to")
    a = ap.parse_args()

    # a bare song name means songs/<name>, the same as everywhere else in mvkit
    if a.song and not os.path.isdir(a.song):
        alt = os.path.join("songs", a.song)
        if os.path.isdir(alt):
            a.song = alt
        else:
            sys.exit("no such song folder: %s (nor %s)" % (a.song, alt))

    if a.emit and not a.song:
        sys.exit("--emit needs --song <name>: the workflows live in the song folder")

    if a.object_info:
        with open(a.object_info, encoding="utf-8") as fh:
            info = json.load(fh)
        print("read %d node types from %s" % (len(info), a.object_info))
        print()
    else:
        info = fetch(a.host, "/object_info")
    report(info, a.object_info or a.host)
    if a.emit:
        emit(info, None, a.song)


if __name__ == "__main__":
    main()

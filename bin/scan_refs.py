#!/usr/bin/env python3
"""Read _source/refs/ and work out the H3 reference tags.

  scan_refs.py <song-dir>

Naming schema (the number is optional and only sets load order):

  [NN_]char_<slug>.png    a character            -> <Picture n>
  [NN_]style_<slug>.png   a look / colour board  -> <Picture n>
  [NN_]loc_<slug>.png     a location or set      -> <Picture n>
  [NN_]prop_<slug>.png    a prop                 -> <Picture n>
  [NN_]video_<slug>.mp4   a motion reference     -> <Video n>

H3 renumbers tags over the slots you actually connect, and a reference video's
own soundtrack takes an <Audio> number before any standalone audio - so the scene
mp3 is not always <Audio 1>. This computes the real numbers and writes
_source/refs.json for build_storyboards.py.
"""
import json, os, re, sys

IMG = (".png", ".jpg", ".jpeg", ".webp")
VID = (".mp4", ".mov", ".webm")
KINDS = ("char", "style", "loc", "prop", "video")
LIMITS = {"images": 9, "videos": 3, "audio": 3, "media": 12}
NAME = re.compile(r"^(?:(\d+)[_-])?(%s)[_-](.+)$" % "|".join(KINDS), re.I)


def scan(song):
    refs = os.path.join(song, "_source", "refs")
    images, videos, skipped = [], [], []
    for f in sorted(os.listdir(refs)) if os.path.isdir(refs) else []:
        # __*.txt are this folder's own notes, not references
        if f.startswith((".", "__")) or os.path.isdir(os.path.join(refs, f)):
            continue
        stem, ext = os.path.splitext(f)
        m = NAME.match(stem)
        if not m or ext.lower() not in IMG + VID:
            skipped.append(f)
            continue
        order, kind, slug = int(m.group(1) or 999), m.group(2).lower(), m.group(3)
        item = {"file": "_source/refs/" + f, "kind": kind,
                "slug": slug.replace("_", " ").replace("-", " ").strip(),
                "order": order}
        (videos if ext.lower() in VID or kind == "video" else images).append(item)
    for lst in (images, videos):
        lst.sort(key=lambda i: (i["order"], i["file"]))
    return images, videos, skipped


def main():
    song = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/")
    images, videos, skipped = scan(song)

    warn = []
    for key, lst in (("images", images), ("videos", videos)):
        if len(lst) > LIMITS[key]:
            warn.append("%d %s but H3 takes %d - the extras are dropped"
                        % (len(lst), key, LIMITS[key]))
            del lst[LIMITS[key]:]
    for n, i in enumerate(images, 1):
        i["tag"] = "<Picture %d>" % n
    for n, v in enumerate(videos, 1):
        v["tag"] = "<Video %d>" % n
        v["audio_tag"] = "<Audio %d>" % n          # a video's own track claims a number

    # the scene mp3 is a standalone audio input, queued behind the videos' tracks
    scene_audio = "<Audio %d>" % (len(videos) + 1)
    total = len(images) + len(videos) + 1
    if total > LIMITS["media"]:
        warn.append("%d media inputs but H3 takes %d in total" % (total, LIMITS["media"]))
    if not images and not videos:
        warn.append("no image or video reference - H3 rejects audio-only input")

    out = {"images": images, "videos": videos, "scene_audio_tag": scene_audio,
           "media_total": total, "warnings": warn}
    dst = os.path.join(song, "_source", "refs.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for i in images + videos:
        print("  %-12s %-6s %-28s %s" % (i["tag"], i["kind"], i["slug"],
                                         os.path.basename(i["file"])))
    print("  %-12s audio  this scene's slice of the song" % scene_audio)
    print("media inputs : %d of %d" % (total, LIMITS["media"]))
    for f in skipped:
        print("! ignored (name does not match the schema): %s" % f)
    for w in warn:
        print("! " + w)
    print("wrote %s" % dst)


if __name__ == "__main__":
    main()

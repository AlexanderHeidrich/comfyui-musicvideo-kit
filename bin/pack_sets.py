#!/usr/bin/env python3
"""_source/scenes.json -> the set-*/ deliverable.

Files what an agent wrote. It never writes prose: every word of every prompt
comes out of scenes.json exactly as it went in. What it does do is the
bookkeeping a person should not: group the scenes that need the same reference
sheets, number those sheets the way H3 will number them, and refuse to ship a
prompt that breaks a documented H3 limit.

The grouping is not a nicety. A saved ComfyUI graph cannot change how many links
it has, so the set of connected reference images is fixed for a whole graph -
and a connected reference turns up on screen whether the prompt asks for it or
not. Scenes needing the same sheets therefore share a folder and a graph.
"""

import json
import os
import re
import shutil
import sys

MAX_PROMPT = 7000               # every published H3 guide states this
FPS = 24                        # the Drehbuch's own basis; 243 frames = 10.125 s
SECTIONS = ["subject_definitions", "summary", "retention_analysis",
            "detailed_description", "overall_soundscape", "non_diegetic_music"]
FRAMING = re.compile(r"\b(close-?up|wide shot|medium shot|extreme close|"
                     r"long shot|totale|halbtotale|establishing shot)\b", re.I)


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def slug(text, cap=34):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:cap].rstrip("-") or "scene")


def read_refs(song):
    """refs/ -> {slug: (order, filename)}, ordered by the NN_ prefix."""
    d = os.path.join(song, "refs")
    if not os.path.isdir(d):
        die("%s has no refs/ folder" % song)
    out = {}
    for fn in sorted(os.listdir(d)):
        m = re.match(r"^(\d+)_(char|style|loc|prop)_(.+)\.(png|jpg|jpeg|webp)$",
                     fn, re.I)
        if m:
            out[m.group(3).replace("-", " ")] = (int(m.group(1)), fn)
    if not out:
        die("no reference images in %s - see refs/__README.txt for the naming" % d)
    return out


def timecode(frame):
    f = int(round(frame))
    return "%02d:%02d:%02d:%02d" % (f // (FPS * 3600), f // (FPS * 60) % 60,
                                    f // FPS % 60, f % FPS)


def write_timeline(song, rows):
    """(scene, set, render, beat, frames, title) -> __TIMELINE.tsv.

    Laid out off the Drehbuch's own frame numbers from the earliest beat, so the
    Vorspann's negative frames land at the head and the music starts where frame
    0 does. A beat sitting inside a longer one is a layer, not a cut - the
    daydreams play over the hopping loop plate - so it gets track V2.
    """
    if any(len(r[3] or []) != 2 for r in rows):
        return None, ["  ! a scene has no beat [start, end] in scenes.json, so "
                      "no __TIMELINE.tsv was written"]
    zero = min(r[3][0] for r in rows)
    warn, lines = [], ["\t".join(["scene", "tc", "start_s", "dur_s", "track",
                                  "set", "render", "title"])]
    for n, folder, render, beat, frames, title in sorted(rows):
        held = beat[1] - beat[0]
        inside = any(o[0] != n and o[3][0] <= beat[0] and beat[1] <= o[3][1]
                     and (o[3][1] - o[3][0]) > held for o in rows)
        lines.append("\t".join([
            str(n), timecode(beat[0] - zero), "%.3f" % ((beat[0] - zero) / FPS),
            "%.3f" % (held / FPS), "V2" if inside else "V1", folder, render,
            title]))
        if held > frames:
            warn.append("  ! scene %d holds %.3f s but renders %.3f s - loop or "
                        "hold it in the edit" % (n, held / FPS, frames / FPS))
    with open(os.path.join(song, "__TIMELINE.tsv"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return timecode(-zero), warn


def check(scene, variant, text, refs_used):
    """Hard limits first, then the mistakes that cost a re-render."""
    where = "scene %s %s" % (scene.get("scene"), variant)
    n = len(text)
    if n > MAX_PROMPT:
        die("%s is %d characters, over H3's %d. Shorten the action or the "
            "[subject] blocks - do not let a script truncate it, it would cut "
            "the shot off the end." % (where, n, MAX_PROMPT))
    missing = [s for s in SECTIONS if not re.search(r"^%s\s*$" % s, text, re.M)]
    if missing:
        die("%s is missing the section(s): %s" % (where, ", ".join(missing)))
    order = [text.index(s) for s in SECTIONS if s in text]
    if order != sorted(order):
        die("%s has the six sections out of order" % where)

    warn = []
    if "<Audio" in text:
        warn.append("names an <Audio> reference, but no audio is wired any more")
    body = text.split("detailed_description", 1)[-1]
    if "The scene is" not in body.split("[Shot 1]")[0]:
        warn.append("has no location sentence before [Shot 1]")
    for part in re.split(r"\[Shot \d+\]", body)[1:]:
        # the framing lives in the camera sentence; the action must not repeat it
        para = part.split("\n\n", 1)
        if len(para) > 1 and FRAMING.search(para[1]):
            warn.append("the action names a framing - it is reused verbatim "
                        "across v1/v2/v3 and will contradict two of them")
            break
    for word in refs_used:
        if word not in text:
            warn.append("connects %s but never mentions it" % word)
    return ["  ! %s: %s" % (where, w) for w in warn], n


def main():
    if len(sys.argv) < 2:
        die("usage: pack_sets.py <song folder>")
    song = sys.argv[1].rstrip("/")
    name = os.path.basename(os.path.abspath(song))
    src = os.path.join(song, "_source", "scenes.json")
    if not os.path.isfile(src):
        die("%s not found. That file is written by the storyboard skill, not by "
            "this script - see .claude/skills/storyboard/SKILL.md" % src)
    with open(src, encoding="utf-8") as fh:
        doc = json.load(fh)

    refs = read_refs(song)
    scenes = doc.get("scenes") or []
    if not scenes:
        die("scenes.json lists no scenes")

    # group by the sheet tuple, in reference order so <Picture n> is deterministic
    groups, warnings, longest = {}, [], {}
    for sc in scenes:
        sheets = sc.get("sheets") or []
        unknown = [s for s in sheets if s not in refs]
        if unknown:
            die("scene %s names sheet(s) with no image in refs/: %s"
                % (sc.get("scene"), ", ".join(unknown)))
        key = tuple(sorted(sheets, key=lambda s: refs[s][0]))
        groups.setdefault(key, []).append(sc)

    for sc in scenes:
        tags = ["<Picture %d>" % (i + 1) for i in
                range(len(sc.get("sheets") or []))]
        for v, text in sorted((sc.get("prompts") or {}).items()):
            w, n = check(sc, v, text, tags)
            warnings += w
            if n > longest.get(v, (0, None))[0]:
                longest[v] = (n, sc.get("scene"))

    for old in sorted(os.listdir(song)):
        if old.startswith("set-") and os.path.isdir(os.path.join(song, old)):
            shutil.rmtree(os.path.join(song, old))

    index, rows, tl = [], [], []
    order = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    for i, (key, members) in enumerate(order, 1):
        nums = "-".join("%d" % refs[s][0] for s in key)
        folder = "set-%02d_%s" % (i, nums)
        path = os.path.join(song, folder)
        os.makedirs(path, exist_ok=True)
        head = ["scene", "frames", "prompts", "refs", "title"]
        lines = ["\t".join(head)]
        for sc in sorted(members, key=lambda s: int(s["scene"])):
            n, title = int(sc["scene"]), sc.get("title") or ""
            stem = "%02d_%s" % (n, slug(title))
            files = []
            for v, text in sorted((sc.get("prompts") or {}).items()):
                fn = "%s-%s.txt" % (stem, v)
                with open(os.path.join(path, fn), "w", encoding="utf-8") as fh:
                    fh.write(text if text.endswith("\n") else text + "\n")
                files.append(fn)
            lines.append("\t".join([str(n), str(sc.get("frames") or 243),
                                    " ".join(files), nums, title]))
            rows.append((n, folder, title, sc.get("location") or "", nums))
            tl.append((n, folder,
                       "%s/%s" % (folder, files[0][:-4]) if files else "",
                       sc.get("beat") or [], int(sc.get("frames") or 243), title))
        with open(os.path.join(path, "__SCENES.tsv"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        index.append((folder, key, len(members)))

    with open(os.path.join(song, "__SCENES.tsv"), "w", encoding="utf-8") as fh:
        fh.write("scene\tset\ttitle\tlocation\trefs\n")
        for r in sorted(rows):
            fh.write("\t".join(str(x) for x in r) + "\n")

    music_tc, tl_warnings = write_timeline(song, tl)
    warnings += tl_warnings

    with open(os.path.join(song, "__READ_ME.txt"), "w", encoding="utf-8") as fh:
        fh.write(readme(name, index, refs, len(scenes), music_tc))

    print("%s: %d scenes in %d sets" % (name, len(scenes), len(index)))
    for folder, key, count in index:
        print("  %-24s %2d scenes  %s" % (folder, count, ", ".join(key)))
    if longest:
        print("longest prompt: " + "  ".join(
            "%s %d (scene %s)" % (v, n, s) for v, (n, s) in sorted(longest.items())))
    if warnings:
        print("\n%d warning(s):" % len(warnings))
        print("\n".join(warnings))


def readme(name, index, refs, total, music_tc):
    out = ["%s - %d scenes in %d reference sets" % (name, total, len(index)),
           "=" * 74, "",
           "Every clip is 243 frames (10.125 s). Set the H3 node's length to 243",
           "once; it never changes. There is no audio reference and no audio in",
           "these folders - lay the song under the picture in the edit.", ""]
    if music_tc:
        out += ["__TIMELINE.tsv is the edit list: one row per scene with the",
                "timecode it starts at, how long it holds (dur_s - mostly less",
                "than the 10.125 s rendered, so trim), the track, and the render",
                "the clip comes from. It is laid out at %s fps off the Drehbuch's" % FPS,
                "own frame numbers, so the film starts at 00:00:00:00 and DROP",
                "THE MP3 AT %s - the frames before that are the" % music_tc,
                "Vorspann. A V2 row is a layer over the V1 clip underneath it,",
                "not a cut.", "",
                "ComfyUI appends its own counter, so the render column names a",
                "prefix: set-NN_x/07_slug-v1 lands as 07_slug-v1_00001_.mp4, and",
                "-v2/-v3 are the same moment from another angle.", ""]
    out += [
           "BEFORE ANYTHING ELSE: copy every png in this song's refs/ folder into",
           "your ComfyUI/input/ directory. ComfyUI's LoadImage only ever reads",
           "from there, and the graphs name the sheets by bare filename on purpose",
           "so they keep working on whatever machine ComfyUI runs on. Without that",
           "copy, every loader comes up empty.", "",
           "NOT EVERY SHOT SURVIVES ON THE SHEETS ALONE. refs/__PROMPTS.txt ends",
           "with a work list of the images still to be drawn by hand - the props",
           "and the creatures no sheet covers, and the shots worth handing H3 a",
           "finished first frame instead. Read it before you queue anything: the",
           "sheets on that list change which sets exist, and a first frame makes",
           "its scene a set of its own.", "",
           "AND copy comfyui/custom_nodes/watching_hurricanes.py over the one in",
           "your ComfyUI/custom_nodes/, then restart it. The graphs wire that",
           "node's outputs by index, so an older copy shifts every link past the",
           "change: `mvkit probe` compares the two and says so.", "",
           "Each set-*/ folder is a song folder in its own right: open its graph,",
           "put that folder's own path into HurricaneSongFolder's song_path - it",
           "is left empty on purpose, because no absolute path is ever written",
           "into a graph - then set scene_index to increment and the queue's batch",
           "count to scene_count, and press Run once.", "",
           "WIRE THE LOADERS IN THE ORDER LISTED. H3 numbers <Picture n> over the",
           "slots actually connected, so a gap shifts every tag after it and the",
           "prompts stop matching.", ""]
    for folder, key, count in index:
        out.append("%s   (%d scene%s)" % (folder, count, "" if count == 1 else "s"))
        for i, s in enumerate(key, 1):
            out.append("    ref_image_%-2d  <Picture %d>  %s" % (i - 1, i, refs[s][1]))
        out.append("")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main()

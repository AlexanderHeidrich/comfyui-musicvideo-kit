#!/usr/bin/env python3
"""Assemble per-scene storyboard files from the shared blocks plus per-scene content.

  build_storyboards.py <song-dir>

Reads   <song>/_source/scenes.tsv     timing spine (bin/make_scenes.py)
        <song>/_source/bible.txt     constant frame, prepended to every scene
        <song>/_source/style.txt     constant look
        <song>/_source/tail.txt      constant frame, appended to every scene
        <song>/_source/content.json  {"<scene>": {title, lyrics, shot1, shot2}}
Writes  <song>/NN_slug-v{1,2,3}.txt   three camera setups per scene, flat, beside
                                     the single NN_slug.mp3 they all share
        <song>/ALL_scenes.txt         every scene in one file, for a batch run

Edit _source/style.txt once and re-run; nothing is duplicated by hand.
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


def refs_block(song):
    """the live H3 tags from _source/refs.json, or the generic line"""
    path = os.path.join(song, "_source", "refs.json")
    if not os.path.isfile(path):
        return ["picture_1 = the character reference",
                "audio_1   = this window of the song"]
    r = json.load(open(path, encoding="utf-8"))
    out = ["%-11s %-6s %s" % (i["tag"], i["kind"], i["slug"])
           for i in r.get("images", []) + r.get("videos", [])]
    out.append("%-11s audio  this window of the song" % r.get("scene_audio_tag", "<Audio 1>"))
    return out


def tc(s):
    s = float(s)
    return "%02d:%06.3f" % (int(s) // 60, s % 60)


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "scene"


def main():
    song = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "."
    name = os.path.basename(os.path.abspath(song))
    SRC = os.path.join(song, "_source")
    R = lambda p: strip_comments(open(os.path.join(SRC, p), encoding="utf-8").read())
    bible, style, tail = R("bible.txt"), R("style.txt"), R("tail.txt")
    content = json.load(open(os.path.join(SRC, "content.json"), encoding="utf-8"))
    rows = list(csv.DictReader(open(os.path.join(SRC, "scenes.tsv"), encoding="utf-8"),
                              delimiter="\t"))
    CAM = read_cameras(SRC)
    refs = refs_block(song)

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
        content[r["scene"]] = {
            "title": r.get("title") or "scene %s" % r["scene"],
            "lyrics": r.get("lyrics_screenplay") or "",
            "shot1": desc[0].strip(),
            "shot2": " ".join(desc[1:]).strip()}
        from_screenplay += 1

    for f in os.listdir(song):                      # clear previous generated output
        if re.match(r"^\d\d_.*-v\d\.txt$", f) or f == "ALL_scenes.txt":
            os.remove(os.path.join(song, f))
    shutil.rmtree(os.path.join(song, "variants"), ignore_errors=True)

    allp = ["# %s - all %d scenes in one file.\n"
            "# Point the storyboard node at this and set batch count = %d.\n"
            % (name.upper(), len(rows), len(rows)),
            "@BIBLE\n" + bible, "\n@STYLE\n" + style]
    n_var = 0

    for r in rows:
        n = int(r["scene"]); c = content[r["scene"]]
        cut, dur = float(r["inner_cut_rel"]), float(r["duration"])
        scene = c["shot1"].strip()
        if c.get("shot2") and cut > 0:
            scene += "\n\nAt 00:%06.3f, cut to [Shot 2].\n%s" % (cut, c["shot2"].strip())

        cutnote = (" - single shot, too short for two" if not cut else
                   "" if r["cut_on_boundary"] == "yes" else
                   " (forced: no lyric boundary nearby)")
        head = ("# " + "=" * 72 + "\n"
                "#  %s\n"
                "#  SCENE %02d of %d   |   %s -> %s   |   %.4f s / %s frames\n"
                "#  Internal cut at %.3f s%s\n#\n"
                "#  Lyrics in this window: %s\n#\n"
                "#  References:  %s\n"
                "# " + "=" * 72 + "\n") % (
            name.upper(), n, len(rows), tc(r["start"]), tc(r["end"]), dur, r["frames"],
            cut, cutnote, c["lyrics"] or "(instrumental)",
            ("\n#               ".join(refs)))

        base = "%s-%s | %s" % (tc(r["start"]), tc(r["end"]), c["title"])
        for tag, (label, cam) in CAM.items():
            vscene = ("CAMERA - %s\n%s\n\nACTION - identical in scene %02d v1 / v2 / v3\n%s"
                      % (label, cam, n, scene))
            vhead = head + ("#  %s - %s. Coverage, not an alternative scene: the ACTION\n"
                            "#  block is identical in v1/v2/v3, only the camera changes. All three\n"
                            "#  share the audio slice %02d_%s.mp3.\n"
                            % (tag.upper(), label, n, slug(c["title"])))
            open(os.path.join(song, "%02d_%s-%s.txt" % (n, slug(c["title"]), tag)),
                 "w", encoding="utf-8").write(
                "%s\n@BIBLE\n%s\n\n@STYLE\n%s\n\n@SCENE %s (%s)\n%s\n\n@TAIL\n%s\n"
                % (vhead, bible, style, base, label, vscene, tail))
            n_var += 1

        allp.append("\n@SCENE %s\n%s" % (base, scene))

    allp.append("\n@TAIL\n" + tail + "\n")
    open(os.path.join(song, "ALL_scenes.txt"), "w", encoding="utf-8").write("\n".join(allp))

    # name each audio slice after its prompt file so the pair sits together
    renamed = 0
    for r in rows:
        n = int(r["scene"]); c = content[r["scene"]]
        dst = os.path.join(song, "%02d_%s.mp3" % (n, slug(c["title"])))
        for cand in (os.path.join(song, "scene_%02d.mp3" % n),
                     os.path.join(song, "audio", "scene_%02d.mp3" % n)):
            if os.path.exists(cand):
                os.replace(cand, dst); renamed += 1; break
    adir = os.path.join(song, "audio")
    if os.path.isdir(adir) and not os.listdir(adir):
        os.rmdir(adir)

    # the folder explains itself, because it is what gets handed over
    total = sum(float(r["duration"]) for r in rows)
    span = max(float(r["end"]) for r in rows) - min(float(r["start"]) for r in rows)
    readme = ["%s - %d scenes over %.1f s of song, %.1f s of clip material%s"
              % (name.upper(), len(rows), span, total,
                 " (scenes overlap - trim in the edit)" if total > span + 1 else ""),
              "=" * 74, "",
              "Every scene is one MiniMax H3 render. The files are paired by prefix:", "",
              "  NN_title.mp3      the exact window of the song for that scene",
              "  NN_title-v1.txt   wide master        }  same action, three cameras -",
              "  NN_title-v2.txt   other angle        }  render two or three and cut",
              "  NN_title-v3.txt   close / detail     }  between them inside the scene",
              "", "  ALL_scenes.txt    every scene in one file, for a batch run", ""]
    if os.path.isdir(os.path.join(song, "_source", "refs")):
        readme += ["References to load, in this order:", ""]
        readme += ["  " + l for l in refs]
        readme += [""]
    readme += ["In ComfyUI: load the reference image(s) into the picture slots and the",
               "scene's own mp3 into the audio slot, paste the -v1 text as the prompt,",
               "and set length to the frame count named in the file header. The header",
               "of every file repeats its own timing, so nothing has to be looked up.",
               "",
               "Do not edit these files - they are regenerated. Edit _source/ and re-run",
               "`mvkit build %s`." % name, ""]
    open(os.path.join(song, "__READ_ME.txt"), "w", encoding="utf-8",
         newline="\n").write("\n".join(readme))

    print("scenes       : %d" % len(rows))
    if from_screenplay:
        print("from drehbuch: %d scene(s) had no content.json entry and used the "
              "screenplay text" % from_screenplay)
    if renamed:
        print("audio pairs : %d slices renamed to match their prompt" % renamed)
    print("prompts     : %d  (3 camera setups per scene)" % n_var)
    print("combined    : ALL_scenes.txt")
    print("style block : %d lines, shared by all %d files"
          % (len(style.splitlines()), len(rows) + n_var + 1))


if __name__ == "__main__":
    main()

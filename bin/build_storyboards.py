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
    out.append("%-12s this window of the song" % refs.get("scene_audio_tag", "<Audio 1>"))
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


def tc(s):
    s = float(s)
    return "%02d:%06.3f" % (int(s) // 60, s % 60)


def slug(t, cap=34):
    s = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "scene"
    if len(s) > cap:                      # filenames stay usable
        s = s[:cap].rsplit("-", 1)[0] or s[:cap]
    return s.strip("-")


def action_of(c, cut):
    """identical in every variant of a scene - that is the whole point of v1/v2/v3"""
    out = c["shot1"].strip()
    if c.get("shot2") and cut > 0:
        out += "\n\nAt 00:%06.3f, cut to [Shot 2].\n%s" % (cut, c["shot2"].strip())
    return out


def prompt_for(c, cam_block, action, bible, style, sound, music, refs):
    summary = c.get("summary") or first_sentences(c["shot1"])
    if c.get("lyrics"):
        summary += ' The lyric sung here is "%s".' % c["lyrics"]
    retention = style + (
        "\n\nHold identical across every scene of this film: the colour model, the\n"
        "line weight, the proportions and the costume of every character named\n"
        "above, and the time of day and weather of the location.")
    body = [
        ("subject_definitions",
         "References supplied with this generation:\n" +
         "\n".join("  " + l for l in refs) + "\n\n" + bible),
        ("summary", summary),
        ("retention_analysis", retention),
        ("detailed_description", cam_block + "\n\n" + action),
        ("overall_soundscape", sound),
        ("non_diegetic_music", music),
    ]
    return "\n\n".join("%s\n%s" % (k, indent(v)) for k, v in body) + "\n"


def write_batch_lists(song, rows, content, cams):
    """Index files for in-graph batching: one absolute path per line, prompts and
    audio in the same order, grouped by frame count so `length` is set once per
    group instead of per scene."""
    d = os.path.join(song, "__batch")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    groups = {}
    for r in rows:
        n = int(r["scene"]); sl = slug(content[r["scene"]]["title"])
        for tag in sorted(cams):
            groups.setdefault((int(r["frames"]), tag), []).append(
                (os.path.abspath(os.path.join(song, "%02d_%s-%s.txt" % (n, sl, tag))),
                 os.path.abspath(os.path.join(song, "%02d_%s.mp3" % (n, sl)))))
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
        fh.write("\nWiring, and why core nodes are not enough: see docs/comfyui-batch.md\n"
                 "Paths are absolute and regenerated - re-run `mvkit build` after moving\n"
                 "the folder.\n")
    return lines


def main():
    song = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "."
    name = os.path.basename(os.path.abspath(song))
    SRC = os.path.join(song, "_source")
    R = lambda p: strip_comments(open(os.path.join(SRC, p), encoding="utf-8").read())
    bible, style, tail = R("bible.txt"), R("style.txt"), R("tail.txt")
    sound, music = split_tail(tail)
    content = json.load(open(os.path.join(SRC, "content.json"), encoding="utf-8"))
    rows = list(csv.DictReader(open(os.path.join(SRC, "scenes.tsv"), encoding="utf-8"),
                              delimiter="\t"))
    CAM = read_cameras(SRC)
    refs = read_refs(song)
    rlines = ref_lines(refs)

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
        if re.match(r"^\d\d_.*-v\d\.txt$", f) or f in ("ALL_scenes.txt", "__SCENES.tsv"):
            os.remove(os.path.join(song, f))
    shutil.rmtree(os.path.join(song, "variants"), ignore_errors=True)

    dsl = ["# %s - all %d scenes in one file, in the storyboard DSL.\n"
           "# This is the ComfyUI node's batch input. The NN_*.txt files beside it\n"
           "# are the same material as finished H3 prompts, for pasting by hand.\n"
           "# Point the storyboard node here and set batch count = %d.\n"
           % (name.upper(), len(rows), len(rows)),
           "@BIBLE\n" + bible, "\n@STYLE\n" + style]
    manifest = [["scene", "start", "end", "frames", "duration", "inner_cut",
                 "audio", "prompts", "lyrics"]]
    n_var = 0

    for r in rows:
        n = int(r["scene"]); c = content[r["scene"]]
        cut, dur = float(r["inner_cut_rel"]), float(r["duration"])
        action = action_of(c, cut)
        sl = slug(c["title"])

        for tag in sorted(CAM):
            label, cam = CAM[tag]
            open(os.path.join(song, "%02d_%s-%s.txt" % (n, sl, tag)),
                 "w", encoding="utf-8", newline="\n").write(
                prompt_for(c, cam, action, bible, style, sound, music, rlines))
            n_var += 1

        dsl.append("\n@SCENE %s-%s | %s\n%s"
                   % (tc(r["start"]), tc(r["end"]), c["title"], action))
        manifest.append([
            "%02d" % n, tc(r["start"]), tc(r["end"]), r["frames"], "%.4f" % dur,
            "%.3f" % cut if cut else "-", "%02d_%s.mp3" % (n, sl),
            " ".join("%02d_%s-%s.txt" % (n, sl, t) for t in sorted(CAM)),
            c["lyrics"] or "(instrumental)"])

    dsl.append("\n@TAIL\n" + tail + "\n")
    open(os.path.join(song, "ALL_scenes.txt"), "w", encoding="utf-8",
         newline="\n").write("\n".join(dsl))
    with open(os.path.join(song, "__SCENES.tsv"), "w", encoding="utf-8",
              newline="\n") as fh:
        for row in manifest:
            fh.write("\t".join(row) + "\n")

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

    batch = write_batch_lists(song, rows, content, CAM)

    total = sum(float(r["duration"]) for r in rows)
    span = max(float(r["end"]) for r in rows) - min(float(r["start"]) for r in rows)
    readme = ["%s - %d scenes over %.1f s of song, %.1f s of clip material%s"
              % (name.upper(), len(rows), span, total,
                 " (scenes overlap - trim in the edit)" if total > span + 1 else ""),
              "=" * 74, "",
              "Every scene is one MiniMax H3 render. Files are paired by prefix:", "",
              "  NN_title.mp3      the exact window of the song for that scene",
              "  NN_title-v1.txt   wide master        }  same action, three cameras -",
              "  NN_title-v2.txt   other angle        }  render two or three and cut",
              "  NN_title-v3.txt   close / detail     }  between them inside the scene",
              "",
              "The -vN.txt files are finished H3 prompts: MiniMax's six sections, no",
              "markup, nothing to strip. Paste one in as the prompt exactly as it is.",
              "",
              "  __SCENES.tsv      frame count, timing and pairing for every scene",
              "  __batch/          line-aligned lists for batching in ComfyUI",
              "  ALL_scenes.txt    the same material in this kit's DSL, which is what",
              "                    the ComfyUI storyboard node reads for a batch run",
              "", "References to load, in this order:", ""]
    readme += ["  " + l for l in rlines]
    readme += ["",
               "Set length to the frame count in __SCENES.tsv - H3 only accepts lengths",
               "where frames %% 17 == 5, and it rounds up, so do not retype it by feel.",
               "",
               "Do not edit these files - they are regenerated. Edit _source/ and re-run",
               "`mvkit build %s`." % name, ""]
    open(os.path.join(song, "__READ_ME.txt"), "w", encoding="utf-8",
         newline="\n").write("\n".join(readme))

    print("scenes      : %d" % len(rows))
    if from_screenplay:
        print("from drehbuch: %d scene(s) had no content.json entry and used the "
              "screenplay text" % from_screenplay)
    if renamed:
        print("audio pairs : %d slices renamed to match their prompt" % renamed)
    print("prompts     : %d  (%d camera setups per scene, six sections each)"
          % (n_var, len(CAM)))
    print("manifest    : __SCENES.tsv")
    print("batch lists : __batch/  (%d groups: %s)"
          % (len(batch), ", ".join("f%d-%s x%d" % b for b in batch[:4])
             + (" ..." if len(batch) > 4 else "")))
    print("dsl         : ALL_scenes.txt  (for the ComfyUI node)")
    if refs and refs.get("warnings"):
        for w in refs["warnings"]:
            print("! refs: %s" % w)


if __name__ == "__main__":
    main()

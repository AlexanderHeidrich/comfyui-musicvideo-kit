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


RETENTION = {
    "char": ("partially_preserved", "the design, proportions, colour model and "
             "every marking are preserved exactly and never drift between scenes; "
             "only the reference's own rendering, its plain backdrop and its cast "
             "shadow are discarded and redrawn in this film's idiom."),
    "prop": ("partially_preserved", "the shape, material and colour of the object "
             "are preserved; the reference's own rendering and backdrop are not."),
    "style": ("attribute_transfer", "the palette, the line weight and the shape of "
              "a shadow are transferred to everything drawn in this shot. The board "
              "itself is never a thing in the scene and is never drawn."),
    "loc": ("partially_preserved", "a background painting. Where this shot is set "
            "in that place its architecture, layout and palette are preserved and "
            "nothing in it is a subject; where the shot is set elsewhere it "
            "contributes nothing."),
    "video": ("weak_reference", "only its camera movement, cutting and rhythm are "
              "referenced."),
}


def summary_prefix(refs):
    """H3's summary opens with the task types the references actually perform."""
    kinds = []
    if not refs or refs.get("images") or refs.get("videos"):
        kinds.append("reference generation")
    if not refs or refs.get("scene_audio_tag"):
        kinds.append("audio reuse")
    return "[%s] " % " + ".join(kinds)


def retention_lines(refs):
    """one line per reference label, with H3's fixed relationship markers"""
    if not refs:
        return ["<Picture 1>: fully_preserved - the character reference.",
                "<Audio 1>: partially_copy - the supplied window of the song is "
                "reused as the audience-only score; the ambience below is added "
                "over it."]
    out = []
    for i in refs.get("images", []) + refs.get("videos", []):
        marker, why = RETENTION.get(i["kind"], ("partially_preserved", "as defined above."))
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
    retention = retention_lines(refs)
    prefix = summary_prefix(refs)

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

    for f in os.listdir(song):                      # clear previous generated output
        if re.match(r"^\d\d_.*-v\d\.txt$", f) or f in ("ALL_scenes.txt", "__SCENES.tsv"):
            os.remove(os.path.join(song, f))
    shutil.rmtree(os.path.join(song, "variants"), ignore_errors=True)

    per_scene_cams = 0
    bad_cam = set()
    dsl = ["# %s - all %d scenes in one file, in the storyboard DSL.\n"
           "# This is the ComfyUI node's batch input. The NN_*.txt files beside it\n"
           "# are the same material as finished H3 prompts, for pasting by hand.\n"
           "# Point the storyboard node here and set batch count = %d.\n"
           % (name.upper(), len(rows), len(rows)),
           "@BIBLE\n" + bible, "\n@STYLE\n" + style]
    manifest = [["scene", "start", "end", "frames", "duration", "inner_cuts",
                 "continuity", "audio", "prompts", "lyrics"]]
    n_var = 0

    for r in rows:
        n = int(r["scene"]); c = content[r["scene"]]
        cuts, dur = cuts_of(r), float(r["duration"])
        cut = cuts[0] if cuts else 0.0
        action = action_of(c, cuts)
        sl = slug(c["title"])

        # a scene may carry its own cameras: v1 is the screenplay's framing, the
        # rest is coverage. Anything it does not define falls back to the template.
        own = c.get("cameras") or {}
        tags = sorted(set(CAM) | set(own))
        for tag in tags:
            cam = (own.get(tag) or "").strip() or (CAM[tag][1] if tag in CAM else "")
            if not cam:
                continue
            cam = camera_sentence(cam, bad_cam)
            open(os.path.join(song, "%02d_%s-%s.txt" % (n, sl, tag)),
                 "w", encoding="utf-8", newline="\n").write(
                prompt_for(c, cam, action, bible, style, sound, music, rlines,
                           retention, prefix))
            n_var += 1
        if own:
            per_scene_cams += 1

        dsl.append("\n@SCENE %s-%s | %s\n%s"
                   % (tc(r["start"]), tc(r["end"]), c["title"], action))
        manifest.append([
            "%02d" % n, tc(r["start"]), tc(r["end"]), r["frames"], "%.4f" % dur,
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

    # name each audio slice after its prompt file so the pair sits together
    renamed = 0
    for r in rows:
        n = int(r["scene"]); c = content[r["scene"]]
        dst = os.path.join(song, "%02d_%s.mp3" % (n, slug(c["title"])))
        if os.path.exists(dst):
            continue
        cands = [os.path.join(song, "scene_%02d.mp3" % n),
                 os.path.join(song, "audio", "scene_%02d.mp3" % n)]
        # a renamed scene leaves its slice behind under the old slug
        cands += sorted(os.path.join(song, f) for f in os.listdir(song)
                        if re.match(r"^%02d_.*\.mp3$" % n, f))
        for cand in cands:
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
    readme += ["",
               "Set length to the frame count in __SCENES.tsv - H3 only accepts lengths",
               "where frames %% 17 == 5, and it rounds up, so do not retype it by feel.",
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
    if renamed:
        print("audio pairs : %d slices renamed to match their prompt" % renamed)
    print("prompts     : %d  (six sections each)" % n_var)
    print("cameras     : %d scene(s) carry their own, %d fall back to the template"
          % (per_scene_cams, len(rows) - per_scene_cams))
    print("manifest    : __SCENES.tsv")
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
    if refs and refs.get("warnings"):
        for w in refs["warnings"]:
            print("! refs: %s" % w)


if __name__ == "__main__":
    main()

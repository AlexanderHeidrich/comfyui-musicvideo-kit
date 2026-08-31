#!/usr/bin/env python3
"""Snap desired scene boundaries onto MiniMax H3's frame grid and write scenes.tsv.

H3 accepts a clip length only where frames % 17 == 5, trained 124..362, and it
rounds UP. Asking for 5.20s silently yields 5.875s, so a video cut to wall-clock
lyric boundaries drifts against its own audio. This picks, for every scene, the
grid length closest to what you wanted, and lays the scenes end to end - so the
audio slice and the rendered clip are the same length by construction and the
cut never drifts.

  make_scenes.py <transcript.json> <out.tsv> --uniform 10
  make_scenes.py <transcript.json> <out.tsv> --drehbuch drehbuch.txt
  make_scenes.py <transcript.json> <out.tsv> --at 0,9.6,19.23,...
  make_scenes.py <transcript.json> <out.tsv> --sections sections.txt

--drehbuch is the screenplay spine: one scene per line, absolute song time, and
the scene titles/descriptions are carried into scenes.tsv for draft_content.py.
sections.txt / --at give the DESIRED boundaries in seconds; the last one is the
end of the last scene.
"""
import argparse, json, re, sys

FPS = 24
GRID = [n for n in range(124, 363) if n % 17 == 5]          # 124..362
GRID_S = [(n, n / FPS) for n in GRID]
MIN_S, MAX_S = GRID_S[0][1], GRID_S[-1][1]


def snap(want):
    """frames whose duration is closest to `want` seconds"""
    return min(GRID_S, key=lambda ns: abs(ns[1] - want))


def snap_up(want):
    """smallest grid length that still covers `want` seconds"""
    for n, d in GRID_S:
        if d >= want - 1e-9:
            return n, d
    return GRID_S[-1]


def parse_t(tok, fps):
    """mm:ss.sss | hh:mm:ss.sss | ss.sss | f<frame> -> seconds"""
    tok = tok.strip()
    if tok[:1] in "fF" and tok[1:].replace(".", "", 1).isdigit():
        return float(tok[1:]) / fps
    parts = tok.split(":")
    if len(parts) == 1:
        return float(parts[0])
    sec = 0.0
    for p in parts:
        sec = sec * 60.0 + float(p)
    return sec


# framing vocabulary as directors actually write it, German and English
FRAMING_TERMS = [
    (r"vogelperspektive|von oben|top ?down|draufsicht", "bird's eye, straight down"),
    (r"drohnenflug|drohne|aerial", "aerial, travelling"),
    (r"over.?shoulder|over the shoulder|ueber die schulter|über die schulter",
     "over the shoulder"),
    (r"frog.?perspektive|frog.?perspective|bodenebene|auf dem boden|grashoehe|"
     r"grashöhe|wurmperspektive", "worm's eye, at ground level"),
    (r"super ?closeup|super ?cut|staerkeres closeup|stärkeres closeup|"
     r"extreme close", "extreme close-up"),
    (r"closeup|close ?up|grossaufnahme|großaufnahme|nahaufnahme", "close-up"),
    (r"halbtotale|medium ?shot", "medium wide"),
    (r"totale|weitwinkel|wide ?shot", "wide"),
    (r"frontalansicht|von vorne|frontal|front on", "front on, eye level"),
    (r"seitenansicht|von der seite|seitlich|seitliche|profil|side on", "profile, side on"),
    (r"von hinten|hinter dem|hinter der|from behind", "from behind"),
    (r"standbild|freeze", "held freeze frame"),
    (r"zoomt raus|zoom raus|zoom ?out|rausgezoomt", "zoom out"),
    (r"zoom auf|zoom ?in|zoom", "zoom in"),
    (r"dolly|kamerafahrt|mitfahrt|tracking", "tracking move"),
    (r"kameradolly", "tracking move"),
    (r"tiefenschaerfe|tiefenschärfe|fokus wechselt|langsamer fokus|rack focus",
     "focus rack"),
    (r"kamera bleibt|statisch|locked off|bleibt stehen", "locked off"),
]


HOLD = re.compile(r"first\s*(?:frame)?\s*<>\s*last", re.I)
# only phrases that actually say "same setup as the shot before" - "Kamera bleibt
# statisch" is a locked-off camera, not a continuation, and a bare "erneut" is
# usually the character doing something again
CONTINUES = re.compile(r"gleiche einstellung|szene bleibt so|kamera bleibt so"
                       r"|weiterhin gleich|gleicher ausschnitt|gleiche ansicht"
                       r"|ansicht erneut|einstellung erneut|wieder die gleiche"
                       r"|von der vorherigen position|fokus wechselt"
                       r"|same setup|unchanged|continues the", re.I)


def framing_of(text):
    """-> the framing terms the screenplay actually asked for, in reading order"""
    low = text.lower()
    hits = []
    for pat, label in FRAMING_TERMS:
        m = re.search(pat, low)
        if m:
            hits.append((m.start(), label))
    out = []
    for _, label in sorted(hits):
        if label not in out:
            out.append(label)
    return ", ".join(out)


def read_drehbuch(path, fps_override=None):
    """-> (fps, [scene]) where scene = (start_s, end_s, title, lyrics, description)

    Accepts the screenplay as exported: a free preamble, then one block per
    scene headed by `Frame <a> bis <b>` (or a `<start>-<end> | title | desc`
    line). Quoted text in a block is the lyric it sits on.
    """
    raw = open(path, encoding="utf-8").read()
    fps = fps_override or float(FPS)
    if not fps_override:
        m = (re.search(r"^\s*#?\s*fps\s*[:=]\s*([\d.]+)", raw, re.I | re.M)
             or re.search(r"([\d.]+)\s*FPS", raw, re.I))
        if m:
            fps = float(m.group(1))

    head = re.compile(r"^\s*(?:Frame|Frames|Bild)\s+(-?[\d.]+)\s*(?:bis|to|-|\u2013|\u2192)\s*"
                      r"(-?[\d.]+)\s*$", re.I)
    inline = re.compile(r"^\s*([0-9fF:.]+)\s*(?:-|to|\u2013)\s*([0-9fF:.]+)\s*\|(.*)$")

    scenes, cur = [], None
    for line in raw.splitlines():
        m = head.match(line)
        if m:
            if cur:
                scenes.append(cur)
            cur = [float(m.group(1)) / fps, float(m.group(2)) / fps, []]
            continue
        m = inline.match(line)
        if m:
            if cur:
                scenes.append(cur)
            cols = [c.strip() for c in m.group(3).split("|")]
            cur = [parse_t(m.group(1), fps), parse_t(m.group(2), fps), []]
            cur[2].append(" | ".join(c for c in cols if c))
            continue
        if cur is not None and line.strip():
            if re.match(r"^[\s=_*.\u2013-]+$", line):   # separator rule, not prose
                continue
            cur[2].append(line.strip())
    if cur:
        scenes.append(cur)
    if not scenes:
        sys.exit("no `Frame <a> bis <b>` blocks in %s" % path)

    out = []
    for st, en, body in scenes:
        text = " ".join(body)
        # explicit pairs: a lone \u2019 is an apostrophe (Uns\u2019re), not a quote
        quoted = [g for gs in re.findall(
            r'"([^"]{3,})"|\u201c([^\u201d]{3,})\u201d|\u201e([^\u201c]{3,})\u201c'
            r'|\u2018([^\u2019]{3,})\u2019', text) for g in gs if g]
        lyrics = " / ".join(q.strip() for q in quoted)
        desc = text
        for q in quoted:                                  # keep the prose, drop the quotes
            desc = desc.replace(q, " ")
        desc = re.sub(r'[\"\u201c\u201d\u201e\u2018\u2019]', "", desc)
        desc = re.sub(r"\s{2,}", " ", desc).strip(" .")
        title = lyrics or desc
        title = " ".join(title.split()[:5])
        out.append((st, en, title, lyrics, desc, framing_of(text),
                    bool(HOLD.search(text)), bool(CONTINUES.search(text))))
    out.sort()
    return fps, out


def fuse_holds(scenes, max_s):
    """`First Frame <> Last Frame` on consecutive, touching scenes means one
    unbroken camera setup. If the run fits inside a single generation it becomes
    one scene with internal cuts at the joins; if it does not, each part after
    the first has to start on the previous clip's last frame."""
    out, notes, i = [], [], 0
    while i < len(scenes):
        sc = dict(scenes[i])
        j = i + 1
        while (sc["hold"] and j < len(scenes) and scenes[j]["hold"]
               and abs(scenes[j]["st"] - scenes[j - 1]["en"]) < 0.05
               and (scenes[j]["en"] - sc["st"]) <= max_s):
            nxt = scenes[j]
            sc["cuts"].append(round(nxt["st"] - sc["st"], 3))
            sc["shots"].append(nxt["desc"])
            sc["en"] = nxt["en"]
            sc["lyrics"] = " / ".join(x for x in (sc["lyrics"], nxt["lyrics"]) if x)
            sc["desc"] = (sc["desc"] + " || " + nxt["desc"]).strip(" |")
            sc["framing"] = sc["framing"] or nxt["framing"]
            j += 1
        if j > i + 1:
            notes.append("scenes at %.2fs..%.2fs are one held setup (%.2fs) - fused into "
                         "one generation with %d internal cut(s)"
                         % (scenes[i]["st"], sc["en"], sc["en"] - sc["st"], len(sc["cuts"])))
        out.append(sc)
        i = j
    # what is left held and touching its predecessor has to chain off its last frame
    for k, sc in enumerate(out):
        # a hold marker means the shot loops, not that it continues the one before
        sc["chain"] = bool(k and sc["cont"]
                           and abs(sc["st"] - out[k - 1]["en"]) < 0.05)
    return out, notes


def merge_short(scenes, min_s):
    """--merge-short: group consecutive scenes until the group is long enough to
    render, so you get fewer clips. A group closes as soon as it clears min_s."""
    out, notes, cur = [], [], None

    def dur(g):
        return g["en"] - g["st"]

    for sc in scenes:
        if cur is not None and dur(cur) < min_s:
            notes.append("scene at %.2fs (%.2fs) merged into the scene starting %.2fs"
                         % (sc["st"], sc["en"] - sc["st"], cur["st"]))
            cur["cut_hint"] = cur.get("cut_hint") or sc["st"]
            cur["en"] = max(cur["en"], sc["en"])
            cur["lyrics"] = " / ".join(x for x in (cur["lyrics"], sc["lyrics"]) if x)
            cur["desc"] = (cur["desc"] + " || " + sc["desc"]).strip(" |")
            cur["title"] = cur["title"] or sc["title"]
            cur["framing"] = cur.get("framing") or sc.get("framing", "")
        else:
            if cur is not None:
                out.append(cur)
            cur = dict(sc)
        if dur(cur) >= min_s:
            out.append(cur); cur = None
    if cur is not None:
        if out:
            notes.append("trailing scene at %.2fs merged back" % cur["st"])
            out[-1]["en"] = max(out[-1]["en"], cur["en"])
            out[-1]["desc"] = (out[-1]["desc"] + " || " + cur["desc"]).strip(" |")
            out[-1]["lyrics"] = " / ".join(x for x in (out[-1]["lyrics"], cur["lyrics"]) if x)
            out[-1]["framing"] = out[-1].get("framing") or cur.get("framing", "")
        else:
            out.append(cur)
    return out, notes


def lyrics_for(segments, a, b):
    hit = [s["text"] for s in segments if s["start"] < b - 0.15 and s["end"] > a + 0.15]
    return " / ".join(hit)


def lay_end_to_end(want, warn):
    """--uniform / --at / --sections: scenes butt up against each other, so the
    render never drifts against its own audio."""
    rows, t = [], want[0]
    for i in range(len(want) - 1):
        target = want[i + 1] - t
        if target < MIN_S - 0.6:
            warn.append("scene %d wanted %.2fs, below H3 minimum %.2fs - merged into it"
                        % (len(rows) + 1, target, MIN_S))
            continue
        target = min(max(target, MIN_S), MAX_S)
        n, d = snap(target)
        rows.append({"scene": len(rows) + 1, "start": round(t, 3), "end": round(t + d, 3),
                     "frames": n, "dur": round(d, 4),
                     "drift": round((t + d) - want[i + 1], 3)})
        t += d
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript"); ap.add_argument("out")
    ap.add_argument("--at", help="comma separated desired boundaries in seconds")
    ap.add_argument("--sections", help="file with one boundary per line")
    ap.add_argument("--drehbuch", help="screenplay spine: <start>-<end> | title | description")
    ap.add_argument("--fps", type=float,
                    help="frame rate of f<n> values in the drehbuch (default: its header, else 24)")
    ap.add_argument("--uniform", type=float,
                    help="tile the whole song with scenes of this length instead")
    ap.add_argument("--merge-short", action="store_true",
                    help="group short drehbuch scenes into fewer, longer scenes")
    ap.add_argument("--inner-cut", type=float, default=5.5,
                    help="target time inside each scene for the internal cut")
    a = ap.parse_args()

    meta = json.load(open(a.transcript, encoding="utf-8"))
    dur, segs = meta["duration"], meta["segments"]

    rows, warn = [], []
    if a.drehbuch:
        fps, parsed = read_drehbuch(a.drehbuch, a.fps)
        print("drehbuch: %d scenes, frame numbers read at %g fps (H3 renders at %d fps)"
              % (len(parsed), fps, FPS))
        scenes = [{"st": st, "en": en, "title": ti, "lyrics": ly, "desc": de,
                   "framing": fr, "hold": ho, "cont": co, "cut_hint": None,
                   "cuts": [], "shots": [de]}
                  for st, en, ti, ly, de, fr, ho, co in parsed]
        # blocks that end before the music starts are the Vorspann: kept as scene 0,
        # a clip with no window of the song behind it
        pre = [sc for sc in scenes if sc["en"] <= 0.02]
        preroll = []
        if pre:
            nf, d = snap_up(max(sum(sc["en"] - sc["st"] for sc in pre), MIN_S))
            preroll = [{"scene": 0, "start": None, "end": None, "frames": nf,
                        "dur": round(d, 4), "drift": 0.0,
                        "title": pre[0]["title"] or "vorspann",
                        "screenplay": " || ".join(sc["desc"] for sc in pre),
                        "lyrics_dreh": "", "framing": pre[0].get("framing", ""),
                        "hold": False, "chain": False, "fused_cuts": [],
                        "shots": [], "cut_hint": None, "lyrics": "",
                        "cut_rel": 0.0, "cut_snapped": False, "cuts": []}]
            warn.append("%d scene(s) end before the music starts - kept as scene 0, "
                        "%.3fs with no audio reference" % (len(pre), d))
        scenes = [sc for sc in scenes if sc["en"] > 0.02]
        for sc in scenes:
            sc["st"] = max(0.0, sc["st"])
        scenes, held_notes = fuse_holds(scenes, MAX_S)
        warn.extend(held_notes)
        if a.merge_short:
            scenes, notes = merge_short(scenes, MIN_S)
            warn.extend(notes)
        # every scene keeps its own start. Too short -> padded to H3's minimum and
        # it simply overlaps the next scene. Too long -> split into parts.
        pads, splits = 0, 0
        for sc in scenes:
            want_d = sc["en"] - sc["st"]
            parts = [(sc["st"], want_d, "")]
            if want_d < MIN_S:
                pads += 1
                parts = [(sc["st"], MIN_S, "")]
            elif want_d > MAX_S:
                n_parts = int(want_d // MAX_S) + (1 if want_d % MAX_S > 0.01 else 0)
                splits += 1
                parts, t0, left = [], sc["st"], want_d
                for k in range(n_parts):
                    take = min(MAX_S, left)
                    parts.append((t0, take, " [part %d/%d]" % (k + 1, n_parts)))
                    t0 += snap_up(take)[1] if take >= MIN_S else MIN_S
                    left -= take
            for st, want_p, tag in parts:
                n, d = snap_up(max(want_p, MIN_S))
                rows.append({"scene": len(rows) + 1, "start": round(st, 3),
                             "end": round(st + d, 3), "frames": n, "dur": round(d, 4),
                             "drift": round(d - want_p, 3),
                             "title": (sc["title"] + tag).strip(),
                             "screenplay": sc["desc"], "lyrics_dreh": sc["lyrics"],
                             "framing": sc.get("framing", ""),
                             "hold": sc.get("hold", False),
                             "chain": sc.get("chain", False) and not tag,
                             "fused_cuts": sc.get("cuts", []) if not tag else [],
                             "shots": sc.get("shots", []) if not tag else [],
                             "cut_hint": sc["cut_hint"] if not tag else None})
        if pads:
            warn.append("%d scene(s) were shorter than H3's %.2fs minimum - padded, so "
                        "they overlap what follows; trim in the edit" % (pads, MIN_S))
        if splits:
            warn.append("%d scene(s) were longer than H3's %.2fs maximum - split into "
                        "consecutive parts" % (splits, MAX_S))
        rows = preroll + rows
        if rows and rows[-1]["end"] > dur + 0.5:
            warn.append("the last scene ends %.2fs past the song (%.2fs); its tail is silent"
                        % (rows[-1]["end"] - dur, dur))
        want = None
    elif a.uniform:
        n_f, d = snap(a.uniform)
        want, t = [0.0], 0.0
        while t + d <= dur + 0.25:
            t += d; want.append(round(t, 4))
        rest = dur - t
        if rest >= MIN_S - 0.25:                      # tail long enough for H3
            want.append(round(t + snap(rest)[1], 4))
        print("uniform mode: %d frames = %.4f s per scene" % (n_f, d))
    elif a.at:
        want = [float(x) for x in a.at.replace("\n", ",").split(",") if x.strip()]
    elif a.sections:
        want = [float(l.split("#")[0]) for l in open(a.sections)
                if l.split("#")[0].strip()]
    else:
        sys.exit("need --at or --sections")
    if want is not None:
        want = sorted(set(want))
        if len(want) < 2:
            sys.exit("need at least 2 boundaries")
        rows = lay_end_to_end(want, warn)

    if not rows:
        sys.exit("no scenes")

    # internal cut: nearest ASR segment boundary to the target, so the cut never
    # lands mid-word. Falls back to the raw target when no boundary is close.
    bounds = sorted({round(x, 3) for s_ in segs for x in (s_["start"], s_["end"])})
    for r in rows:
        if r["start"] is None:                        # the Vorspann has no audio
            continue
        r["lyrics"] = lyrics_for(segs, r["start"], r["end"]).replace("\t", " ")
        if r.get("fused_cuts"):
            r["cuts"] = list(r["fused_cuts"])
            r["cut_rel"], r["cut_snapped"] = r["cuts"][0], True
            continue
        # a scene too short to hold two shots gets no internal cut at all
        if r["dur"] < a.inner_cut + 2.5:
            r["cut_rel"], r["cut_snapped"], r["cuts"] = 0.0, False, []
            continue
        lo, hi = r["start"] + 3.0, r["end"] - 2.5
        # a scene built from two merged scenes cuts where the second one starts
        target = r.get("cut_hint") or (r["start"] + a.inner_cut)
        target = min(max(target, lo), hi)
        cand = [b for b in bounds if lo <= b <= hi]
        r["cut"] = round(min(cand, key=lambda b: abs(b - target)) if cand else target, 3)
        r["cut_rel"] = round(r["cut"] - r["start"], 3)
        r["cut_snapped"] = bool(cand)
        r["cuts"] = [r["cut_rel"]]

    # tl_frame is the frame the clip sits on in the edit; start/end stay the window
    # of the song each clip takes its audio from, so prepending the Vorspann moves
    # the picture without moving the sound
    offset = sum(r["frames"] for r in rows if r["start"] is None)
    for r in rows:
        r["tl"] = 0 if r["start"] is None else int(round(r["start"] * FPS)) + offset

    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("scene\tstart\tend\tframes\tduration\ttl_frame\tinner_cut_rel"
                 "\tcut_on_boundary\tlyrics_asr\ttitle\tlyrics_screenplay\tframing"
                 "\tcontinuity\tinner_cuts\tscreenplay\n")
        for r in rows:
            fh.write("%d\t%s\t%s\t%d\t%.4f\t%d\t%.3f\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" %
                     (r["scene"],
                      "-" if r["start"] is None else "%.3f" % r["start"],
                      "-" if r["end"] is None else "%.3f" % r["end"],
                      r["frames"], r["dur"], r["tl"],
                      r["cut_rel"], "yes" if r["cut_snapped"] else "no", r["lyrics"],
                      r.get("title", "").replace("\t", " "),
                      r.get("lyrics_dreh", "").replace("\t", " "),
                      r.get("framing", "").replace("\t", " "),
                      ",".join(x for x in (("hold" if r.get("hold") else ""),
                                           ("chain" if r.get("chain") else "")) if x),
                      ",".join("%.3f" % x for x in r.get("cuts", [])),
                      r.get("screenplay", "").replace("\t", " ")))

    music = [r for r in rows if r["start"] is not None]
    print("scenes            : %d%s"
          % (len(rows), " (incl. scene 0, no audio)" if len(music) != len(rows) else ""))
    print("covers           : %.3f -> %.3f s  (song %.3f s, %+.3f)"
          % (music[0]["start"], music[-1]["end"], dur, music[-1]["end"] - dur))
    print("durations        : %.3f .. %.3f s  (all on the 17k+5 grid: %s)"
          % (min(r["dur"] for r in rows), max(r["dur"] for r in rows),
             all(r["frames"] % 17 == 5 for r in rows)))
    if a.drehbuch:
        print("longest tail     : +%.3f s of clip past its scene, trim in the edit"
              % max(r["drift"] for r in music))
        print("anchoring        : every scene starts on its screenplay frame, so clips"
              " overlap slightly instead of drifting")
    else:
        print("worst drift      : %+.3f s vs the boundary you asked for"
              % max((r["drift"] for r in rows), key=abs))
        print("cumulative drift : none by construction (scenes are laid end to end)")
    for w in warn: print("! " + w)
    print()
    snapped = sum(1 for r in rows if r["cut_snapped"])
    nocut = sum(1 for r in rows if r["cut_rel"] == 0.0)
    print("inner cuts       : %d on a real segment boundary, %d forced, %d single-shot scenes"
          % (snapped, len(rows) - snapped - nocut, nocut))
    print()
    print("scene  start    end     frames  dur      cut@   on-bnd")
    for r in rows:
        print("%3d  %7s %7s   %4d   %6.3f  %6.3f  %-5s  %s"
              % (r["scene"],
                 "-" if r["start"] is None else "%7.3f" % r["start"],
                 "-" if r["end"] is None else "%7.3f" % r["end"],
                 r["frames"], r["dur"],
                 r["cut_rel"], "yes" if r["cut_snapped"] else ("-" if r["cut_rel"]==0 else "NO"),
                 ((r.get("lyrics_dreh") or r.get("title") or r["lyrics"])[:44]
                  or "(instrumental)")))


if __name__ == "__main__":
    main()

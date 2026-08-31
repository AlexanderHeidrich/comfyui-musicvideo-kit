#!/usr/bin/env python3
"""Check that the frame grid, the declared seconds and the audio slices agree.

  verify_timing.py <song-dir>

Everything downstream rests on scenes.tsv being exactly right, so this measures
rather than trusts: the grid rule, duration == frames/24, end == start+duration,
each slice's decoded length, and where each slice actually sits in the song.
Exits non-zero if anything is off.
"""
import array, csv, os, subprocess, sys

FPS, SR, TOL_MS = 24, 8000, 2.0


def decode(path):
    out = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-f", "s16le",
                          "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    a = array.array("h")
    a.frombytes(out[:len(out) // 2 * 2])
    return a


def offset_ms(song, sl, start):
    """where the slice really sits, searched +/-60 ms around where it claims to"""
    base, w, r = int(start * SR), min(3000, len(sl)), int(0.060 * SR)
    if w < 500:
        return None
    best = (float("inf"), None)
    for lag in range(-r, r + 1, 4):
        o = base + lag
        if o < 0 or o + w > len(song):
            continue
        s = sum(abs(song[o + i] - sl[i]) for i in range(0, w, 3))
        if s < best[0]:
            best = (s, lag)
    return None if best[1] is None else best[1] / float(SR) * 1000.0


def main():
    song_dir = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/")
    src = os.path.join(song_dir, "_source")
    rows = list(csv.DictReader(open(os.path.join(src, "scenes.tsv"), encoding="utf-8"),
                              delimiter="\t"))
    man_path = os.path.join(song_dir, "__SCENES.tsv")
    man = {}
    if os.path.isfile(man_path):
        lines = open(man_path, encoding="utf-8").read().splitlines()
        head = lines[0].split("\t")
        for l in lines[1:]:
            c = l.split("\t")
            man[c[0]] = dict(zip(head, c))

    problems = []
    silent = 0
    for r in rows:
        sc, f, d = r["scene"], int(r["frames"]), float(r["duration"])
        if r["start"].strip() in ("", "-"):           # a clip with no window of the song
            silent += 1
            if f % 17 != 5 or not 124 <= f <= 362:
                problems.append("scene %s: %d frames is off H3's grid" % (sc, f))
            continue
        st, en = float(r["start"]), float(r["end"])
        if f % 17 != 5:
            problems.append("scene %s: %d frames, but H3 needs frames %% 17 == 5" % (sc, f))
        if not 124 <= f <= 362:
            problems.append("scene %s: %d frames is outside H3's trained 124-362" % (sc, f))
        if abs(d - f / float(FPS)) > 5e-5:
            problems.append("scene %s: duration %.4f != %d/%d = %.4f"
                            % (sc, d, f, FPS, f / float(FPS)))
        if abs((st + d) - en) > 1e-3:
            problems.append("scene %s: end %.3f != start+duration %.3f" % (sc, en, st + d))
        for c in [float(x) for x in (r.get("inner_cuts") or "").split(",") if x.strip()]:
            if not 0 < c < d:
                problems.append("scene %s: internal cut %.3f outside 0..%.3f" % (sc, c, d))
    print("scenes        : %d, frame values %s"
          % (len(rows), sorted({int(r["frames"]) for r in rows})))
    print("grid rule     : %s" % ("ok" if not problems else "FAILED"))

    audio = [os.path.join(src, f) for f in ("song.mp3", "song.wav")
             if os.path.isfile(os.path.join(src, f))]
    if not man or not audio:
        print("audio         : skipped (need __SCENES.tsv and _source/song.*)")
    else:
        song = decode(audio[0])
        print("song          : %.3f s decoded" % (len(song) / float(SR)))
        worst_len, worst_off = 0.0, 0.0
        for r in rows:
            m = man.get("%02d" % int(r["scene"]))
            if not m:
                problems.append("scene %s: not in __SCENES.tsv" % r["scene"]); continue
            if m["audio"].strip() in ("", "-"):       # a clip with no window of the song
                continue
            p = os.path.join(song_dir, m["audio"])
            if not os.path.isfile(p):
                problems.append("scene %s: %s missing" % (r["scene"], m["audio"])); continue
            sl = decode(p)
            dl = (len(sl) / float(SR) - float(r["duration"])) * 1000.0
            if r["start"].strip() in ("", "-"):
                # a slice of silence: its length still has to be exact, but there
                # is no position in the song to compare it against
                worst_len = max(worst_len, abs(dl))
                if abs(dl) > 2.0:
                    problems.append("scene %s: silent slice is %+0.1f ms off its "
                                    "declared length" % (sc, dl))
                continue
            off = offset_ms(song, sl, float(r["start"]))
            worst_len = max(worst_len, abs(dl))
            if abs(dl) > TOL_MS:
                problems.append("scene %s: slice is %+.1f ms off its declared length"
                                % (r["scene"], dl))
            if off is None:
                problems.append("scene %s: could not locate the slice in the song" % r["scene"])
            else:
                worst_off = max(worst_off, abs(off))
                if abs(off) > TOL_MS:
                    problems.append("scene %s: slice sits %+.1f ms from where it claims"
                                    % (r["scene"], off))
        print("slice length  : worst %+.1f ms vs declared (tolerance %.1f)" % (worst_len, TOL_MS))
        print("slice position: worst %+.1f ms vs the original" % worst_off)

    if problems:
        print("\n%d problem(s):" % len(problems))
        for p in problems[:30]:
            print("  ! " + p)
        sys.exit(1)
    print("\neverything agrees")


if __name__ == "__main__":
    main()

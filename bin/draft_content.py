#!/usr/bin/env python3
"""Fill <song>/_source/content.json from the scene grid, the screenplay and the lyrics.

  draft_content.py <song-dir> [--llm] [--force] [--model gemma3:4b]

Without --llm this is deterministic: the screenplay text of each scene becomes
shot1 / shot2 and its quoted lines become the lyric. That is enough to render.
With --llm the same material is rewritten into shot language by a local model
(Ollama or LM Studio, OpenAI-compatible), which is the offline-first path when no
Claude is in the loop. Existing entries are kept unless --force.

env: MVKIT_LLM_URL (default http://127.0.0.1:11434/v1/chat/completions)
     MVKIT_LLM_MODEL (default gemma3:4b)
"""
import argparse, csv, json, os, re, sys, urllib.error, urllib.request

from build_storyboards import read_brief

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = os.environ.get("MVKIT_LLM_URL", "http://127.0.0.1:11434/v1/chat/completions")
MODEL = os.environ.get("MVKIT_LLM_MODEL", "gemma3:4b")


def strip_comments(t):
    return "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("#")).strip()


def read(*parts):
    p = os.path.join(*parts)
    return strip_comments(open(p, encoding="utf-8").read()) if os.path.isfile(p) else ""


# v1 restates the screenplay's framing; v2/v3 are coverage, per
# templates/cameras/__COVERAGE.txt
COVER = {
 "bird":   ("Wide and at eye level, so the space reads as a place rather than a diagram.",
            "Close on the detail the overhead view flattened away."),
 "worm":   ("High and looking down on the same action, which inverts who has the power.",
            "Close on the point of contact with the ground."),
 "ots":    ("The answering over-the-shoulder from the other side of the pair.",
            "A clean single on the same character, without the foreground shoulder."),
 "xcu":    ("The wide that establishes where this happens and who else is present.",
            "The reverse - what the subject is looking at."),
 "cu":     ("The wide that establishes where this happens and who else is present.",
            "The reverse - what the subject is looking at."),
 "wide":   ("Medium on whoever carries the beat, chest up.",
            "The insert: the single object or point of contact the wide cannot show."),
 "mw":     ("Wide, so the whole location reads at once.",
            "Close on the single most specific thing in the action."),
 "profile":("Three-quarter front, where the face reads best.",
            "Extreme close on one feature."),
 "front":  ("Profile, dead side on, the background compressed behind.",
            "Extreme close on one feature."),
 "behind": ("Front on, so the face carries the beat instead of the back.",
            "Close on the detail the rear view hides."),
}
TYPES = [("bird's eye", "bird"), ("worm's eye", "worm"), ("over the shoulder", "ots"),
         ("extreme close-up", "xcu"), ("close-up", "cu"), ("medium wide", "mw"),
         ("wide", "wide"), ("profile", "profile"), ("front on", "front"),
         ("from behind", "behind")]
MOVES = [("tracking move", "[Tracking shot]"), ("zoom out", "[Zoom out]"),
         ("zoom in", "[Zoom in]"), ("aerial", "[Tracking shot]")]


def cameras_from_framing(framing):
    """-> {v1, v2, v3} honouring the director's framing, or {} when none was given"""
    if not framing.strip():
        return {}
    low = framing.lower()
    kind = next((k for term, k in TYPES if term in low), None)
    move = next((m for term, m in MOVES if term in low), "[Static shot]")
    v2, v3 = COVER.get(kind, ("Wide, so the whole location reads at once.",
                              "Close on the single most specific thing in the action."))
    return {"v1": "%s %s, as the screenplay asks for." % (move, framing[0].upper() + framing[1:]),
            "v2": "[Static shot] " + v2,
            "v3": "[Static shot] " + v3}


def timed_lyrics(path):
    """[mm:ss] prefixed lines -> [(seconds, text)]; unprefixed lines are ignored
    for alignment because there is no way to place them."""
    out = []
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*\[(\d+):(\d+(?:\.\d+)?)\]\s*(.+)", line)
        if m:
            out.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3).strip()))
    return sorted(out)


def lyric_for(timed, a, b):
    return " / ".join(t for s, t in timed if a - 0.35 <= s < b - 0.35)


def ask(prompt, model, url, timeout=180):
    body = json.dumps({"model": model, "stream": False, "temperature": 0.4,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"]


def parse_json_block(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in the reply")
    return json.loads(m.group(0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("--llm", action="store_true", help="rewrite via the local model")
    ap.add_argument("--force", action="store_true", help="overwrite existing entries")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--url", default=URL)
    a = ap.parse_args()

    song = a.song.rstrip("/")
    src = os.path.join(song, "_source")
    rows = list(csv.DictReader(open(os.path.join(src, "scenes.tsv"), encoding="utf-8"),
                              delimiter="\t"))
    dst = os.path.join(src, "content.json")
    content = {}
    if os.path.isfile(dst):
        try:
            content = json.load(open(dst, encoding="utf-8"))
        except ValueError:
            content = {}

    timed = timed_lyrics(os.path.join(src, "lyrics.txt"))
    guide = read(src, "drafting.txt") or read(KIT, "templates", "drafting.txt")
    film = read_brief(src) or {}
    style = film.get("style", "")
    # the {S}/{P} placeholders bind a subject to an H3 slot and mean nothing here
    cast = re.sub(r"\{[SP]\}", "it",
                  "\n".join("%s - %s" % (k, v)
                             for k, v in sorted(film.get("subjects", {}).items())))
    examples = read(src, "style_examples.txt")

    kept = drafted = failed = 0
    for r in rows:
        n = r["scene"]
        if n in content and not a.force:
            kept += 1
            continue
        desc = (r.get("screenplay") or "").split(" || ")
        lyrics = (lyric_for(timed, float(r["start"]), float(r["end"]))
                  or r.get("lyrics_screenplay") or "")
        entry = {"title": (r.get("title") or "scene %s" % n).strip(),
                 "lyrics": lyrics,
                 "shot1": desc[0].strip(),
                 "shot2": " ".join(desc[1:]).strip()}
        cams = cameras_from_framing(r.get("framing") or "")
        if cams:
            entry["cameras"] = cams

        if a.llm:
            prompt = (
                "%s\n\n--- LOOK ---\n%s\n\n--- CAST AND WORLD ---\n%s\n"
                "%s\n--- THIS SCENE ---\n"
                "duration: %s s\nlyric sung here: %s\nscreenplay: %s\n"
                "framing the director asked for: %s\n\n"
                "Reply with ONLY a JSON object with the keys title, lyrics, shot1, "
                "shot2. Write title, shot1 and shot2 in ENGLISH whatever language "
                "the screenplay is in. Keep the lyric verbatim in its original "
                "language - never translate it."
                % (guide, style, cast[:2000],
                   ("\n--- STYLE REFERENCES ---\n%s\n" % examples[:1200]) if examples else "",
                   r["duration"], lyrics or "(instrumental)",
                   " || ".join(desc) or "(not given)",
                   r.get("framing") or "(none)"))
            try:
                got = parse_json_block(ask(prompt, a.model, a.url))
                for k in ("title", "lyrics", "shot1", "shot2"):
                    if isinstance(got.get(k), str) and got[k].strip():
                        entry[k] = got[k].strip()
                if lyrics:
                    entry["lyrics"] = lyrics          # never let the model rewrite it
            except (urllib.error.URLError, OSError) as e:
                sys.exit("cannot reach the model at %s (%s)\n"
                         "start it with:  mvkit llm-up" % (a.url, e))
            except (ValueError, KeyError) as e:
                failed += 1
                print("! scene %s: model reply unusable (%s), used the screenplay" % (n, e))

        if not entry["shot1"]:
            print("! scene %s has no screenplay text and no draft - fill it by hand" % n)
        content[n] = entry
        drafted += 1

    json.dump(content, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("drafted     : %d scene(s)%s" % (drafted, " via %s" % a.model if a.llm else ""))
    print("kept        : %d existing entr(y/ies)%s"
          % (kept, " - pass --force to redo them" if kept else ""))
    if failed:
        print("model misses: %d" % failed)
    print("wrote %s" % dst)


if __name__ == "__main__":
    main()

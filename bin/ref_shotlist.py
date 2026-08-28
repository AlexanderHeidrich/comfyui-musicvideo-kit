#!/usr/bin/env python3
"""Work out which reference images a song needs, and write the prompts to make them.

  ref_shotlist.py <song-dir>

Reads _source/bible.txt (the cast) and _source/style.txt (the look) and writes
_source/refs/__SHOTLIST.txt: one block per reference, with the filename the
naming schema expects and a ready-to-paste image prompt built from the film's own
style, so the references cannot fight the style block.

Counts how often each character actually appears, from content.json, so the
ranking reflects this song rather than a guess.
"""
import json, os, re, sys

SLOT_RULE = """HOW MANY, AND IN WHICH SLOTS

H3 numbers <Picture n> over the slots you actually connect, so a gap early on
shifts every tag after it. Fill the slots in a fixed order and never leave an
earlier one empty:

  slot 1-3   the core set, loaded into EVERY scene of the song. These carry the
             consistency: the two characters who are on screen most, plus the
             style board. Their tags then never move.
  slot 4     optional, per scene: the location, or a character who only appears
             in a few scenes. Adding it is safe because it comes after the core.

Do not load all eight into every scene. Every reference the shot does not
contain is something the model has to reconcile with what you asked for, and it
costs you more than the extra coverage buys.

Limits: 9 images, 3 videos, 3 standalone audio, 12 media in total, and the
scene's own mp3 already takes one of those.
"""

SHEET = """  Flat 2D character sheet on a plain mid-grey background, no scenery, no text,
  no border, no logo, no watermark. Full body, standing square to camera, neutral
  pose, arms clear of the torso so the silhouette reads. Even flat lighting.
  Drawn in exactly this idiom:
"""

BOARD = """  A colour and construction board, laid out as a flat grid on plain grey. No
  characters, no scenery, no text, no captions, no borders. Show: eight to twelve
  palette swatches as plain rectangles; three line samples showing brush-and-ink
  taper; one shape shown twice, once with its flat base colour and once with the
  hard-edged shadow tone beside it; and one square of gouache background texture.
  Everything drawn in this idiom:
"""


def strip_comments(t):
    return "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("#")).strip()


def read(src, name):
    p = os.path.join(src, name)
    return strip_comments(open(p, encoding="utf-8").read()) if os.path.isfile(p) else ""


def cast_of(bible):
    """-> [(NAME, description)] from the CAST block. Continuation lines carry the
    same indent as the entry that starts them, so only the NAME pattern splits."""
    NAME = re.compile(r"^\s{1,6}([A-ZÄÖÜ][A-ZÄÖÜ' -]{2,})\s+-\s+(.*)$")
    out, name, body = [], None, []
    for line in bible.splitlines():
        m = NAME.match(line)
        if m:
            if name:
                out.append((name, " ".join(body).strip()))
            name, body = m.group(1).strip(), [m.group(2)]
        elif name and line.strip() and line.startswith(" "):
            body.append(line.strip())
        elif name and not line.startswith(" "):        # a new section closes it
            out.append((name, " ".join(body).strip()))
            name, body = None, []
    if name:
        out.append((name, " ".join(body).strip()))
    return [(n, d) for n, d in out if len(d) > 60]


def counts(song, names):
    """how many scenes each character is actually in"""
    p = os.path.join(song, "_source", "content.json")
    if not os.path.isfile(p):
        return {n: 0 for n in names}
    content = json.load(open(p, encoding="utf-8"))
    text = {n: 0 for n in names}
    for c in content.values():
        blob = " ".join(str(v) for k, v in c.items() if k.startswith("shot")).lower()
        for n in names:
            word = n.split()[-1].lower()               # FROSCH -> frosch
            alt = {"frosch": "frog", "huhn": "hen", "forscher": "researcher"}.get(word)
            stem = word[:8]                            # federphibien ~ federphibium
            if stem in blob or (alt and alt in blob):
                text[n] += 1
    return text


def main():
    song = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/")
    src = os.path.join(song, "_source")
    bible, style = read(src, "bible.txt"), read(src, "style.txt")
    if not style:
        sys.exit("no _source/style.txt - write the look first")
    cast = cast_of(bible)
    if not cast:
        print("! no CAST entries found in bible.txt - listing the style board only")
    hits = counts(song, [n for n, _ in cast])
    cast.sort(key=lambda nd: -hits.get(nd[0], 0))

    out = ["REFERENCE SHOT LIST - %s" % os.path.basename(os.path.abspath(song)).upper(),
           "=" * 74, "",
           "Generate these, save them into this folder under the names given, then run",
           "`mvkit refs <song>` to see the tags they will actually get.", "",
           SLOT_RULE, ""]

    order = 1
    for i, (name, desc) in enumerate(cast):
        n = hits.get(name, 0)
        kind = "char"
        out += ["-" * 74,
                "%02d_%s_%s.png" % (order, kind, re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")),
                "  in %d of the song's scenes%s" % (n, "  <- core set" if i < 2 else ""),
                "", "PROMPT", SHEET.rstrip(), "", "  " + style.split("\n\n")[0].replace("\n", "\n  "),
                "", "  The character:", "  " + desc, ""]
        tags = sorted(set(re.findall(r"<(?:Picture|Video) \d+>", desc)))
        if tags:
            out += ["  NOTE: this entry derives the character from %s, which is a"
                    % ", ".join(tags),
                    "  reference that does not exist yet. Either generate that one first and",
                    "  draw this from it, or rewrite the bible entry so it stands on its own",
                    "  before using this prompt.", ""]
        order += 1

    out += ["-" * 74,
            "%02d_style_board.png" % order,
            "  loaded in every scene  <- core set", "",
            "PROMPT", BOARD.rstrip(), "",
            "  " + style.split("\n\n")[0].replace("\n", "\n  "), ""]
    order += 1

    out += ["-" * 74, "OPTIONAL, ONE AT A TIME IN SLOT 4", "",
            "  %02d_loc_<name>.png    a location, as a background painting with no" % order,
            "                       characters in it: gouache on board, brushy and",
            "                       textured, no outlines, warmer and duller than the",
            "                       figures. One per location that recurs.",
            "  %02d_prop_<name>.png   a prop the story turns on, alone on plain grey."
            % (order + 1), "",
            "Locations worth painting are the ones several scenes share. Check",
            "__SCENES.tsv for which those are.", ""]
    dst = os.path.join(src, "refs", "__SHOTLIST.txt")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("cast found  : %s" % ", ".join("%s (%d scenes)" % (n, hits.get(n, 0))
                                         for n, _ in cast))
    print("wrote %s" % dst)


if __name__ == "__main__":
    main()

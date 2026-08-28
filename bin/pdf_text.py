#!/usr/bin/env python3
"""Pull the text out of a PDF with the stdlib only - no poppler, no pip.

  pdf_text.py <file.pdf> [out.txt]

Handles FlateDecode content streams and ToUnicode CMaps, which is what Google
Docs, Word and LibreOffice exports use. Line breaks come from the text matrix,
so a screenplay keeps its block structure. Scanned PDFs have no text layer and
come out empty - that is not fixable here.
"""
import re, sys, zlib


def streams(data):
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            yield zlib.decompress(m.group(1))
        except Exception:
            continue


def cmap_of(data):
    cmap = {}
    for s in streams(data):
        if b"beginbfchar" not in s and b"beginbfrange" not in s:
            continue
        for blk in re.findall(rb"beginbfchar(.*?)endbfchar", s, re.S):
            for a, b in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                cmap[int(a, 16)] = chr(int(b[:4], 16))
        for blk in re.findall(rb"beginbfrange(.*?)endbfrange", s, re.S):
            for a, b, c in re.findall(
                    rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                lo, hi, dst = int(a, 16), int(b, 16), int(c[:4], 16)
                for i in range(lo, hi + 1):
                    cmap[i] = chr(dst + i - lo)
    return cmap


TOKEN = re.compile(rb"<([0-9A-Fa-f]+)>"                      # hex string
                   rb"|\(((?:\\.|[^\\()])*)\)"               # literal string
                   rb"|([-\d.]+)\s+([-\d.]+)\s+(?:Td|TD)\b"  # text offset
                   rb"|[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+([-\d.]+)\s+([-\d.]+)\s+Tm\b"
                   rb"|(T\*)|(BT)"
                   rb"|/\w+\s+([\d.]+)\s+Tf\b")                # font size


def page_text(s, cmap):
    """-> [(font_size, line)]. Skia/Docs emit one BT..ET run per word: Tm sets the
    origin, the first Td inside the run is its position, later Tds are advances."""
    lines, cur, size, cur_size = [], [], 0.0, 0.0
    prev_y, prev_x_end, tm = None, None, (0.0, 0.0)
    first_td, x_end = True, 0.0

    def flush():
        if cur:
            lines.append((cur_size, "".join(cur)))
        return []

    for m in TOKEN.finditer(s):
        hexs, lit, tdx, tdy, tmx, tmy, star, bt, tf = m.groups()
        if hexs:
            cur.append("".join(cmap.get(int(hexs[i:i + 4], 16), "")
                               for i in range(0, len(hexs), 4)))
            cur_size = max(cur_size, size)
        elif lit is not None:
            cur.append(re.sub(rb"\\([()\\])", rb"\1", lit).decode("latin-1"))
            cur_size = max(cur_size, size)
        elif tf:
            size = float(tf)
        elif bt:
            first_td = True
        elif star:
            cur = flush(); cur_size = 0.0; prev_x_end = None
        elif tmx is not None:
            tm = (float(tmx), float(tmy))
        else:
            dx, dy = float(tdx), float(tdy)
            if first_td:
                x, y = tm[0] + dx, tm[1] + dy
                if prev_y is not None and abs(y - prev_y) > 1.0:
                    cur = flush(); cur_size = 0.0
                elif prev_x_end is not None and x - prev_x_end > 1.0:
                    cur.append(" ")
                prev_y, x_end, first_td = y, x, False
            else:
                x_end += dx
            prev_x_end = x_end
    flush()
    return lines


RULE, SUBRULE = "=" * 74, "-" * 74


def extract(path, width=74):
    """Headings are set in a larger font than the body, so they get a separator -
    that is what makes the output readable as a screenplay."""
    data = open(path, "rb").read()
    cmap = cmap_of(data)
    lines = []
    for s in streams(data):
        if b"Tj" in s or b"TJ" in s:
            lines.extend(page_text(s, cmap))
    lines = [(sz, re.sub(r"[ \t]+", " ", t).strip()) for sz, t in lines]
    lines = [(sz, t) for sz, t in lines if t]
    if not lines:
        return ""

    weight = {}
    for sz, t in lines:                       # body = the size most text is set in
        weight[round(sz, 1)] = weight.get(round(sz, 1), 0) + len(t)
    body = max(weight, key=weight.get)

    out = []
    for sz, t in lines:
        if sz >= body * 1.5:
            out += ["", RULE, t, RULE]
        elif sz >= body * 1.15:
            out += ["", SUBRULE, t]
        else:
            out.append(t)
    txt = "\n".join(out)
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    return txt + "\n"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    t = extract(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(t)
        print("wrote %s  (%d chars, %d lines)" % (sys.argv[2], len(t), t.count("\n")))
    else:
        sys.stdout.write(t)

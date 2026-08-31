#!/usr/bin/env python3
"""Lay a ComfyUI workflow out in columns and put labelled groups around them.

  layout_workflow.py <workflow.json> [-o out.json]

Reads and writes the UI format, because that is the only one that has positions
and groups at all - the API format is a flat map with neither, which is why a
graph that has been through it opens as a heap.

Only `pos` and `groups` are touched. Links, widget values, titles and everything
else are left exactly as they are.

Stdlib only.
"""
import argparse
import json
import os
import re
import sys

# left to right, in the order the signal actually flows
COLUMNS = (
    ("SONG FOLDER", "#3f5159", (
        r"^Hurricane", r"^VHS_LoadAudio$", r"^LoadAudioPath$")),
    ("MODELS", "#443f59", (
        r"Loader$", r"^UNETLoader$", r"^CLIPLoader$", r"^VAELoader$",
        r"^CheckpointLoader", r"^Lora")),
    ("REFERENCE SHEETS", "#3f5945", (
        r"^LoadImage", r"^VHS_LoadImagePath$")),
    ("SETTINGS", "#59533f", (
        r"^Resolution", r"^Primitive", r"^RandomNoise$", r"^KSamplerSelect$",
        r"^Comfy(Switch|Math)", r"^Note$", r"^MarkdownNote$")),
    ("H3", "#593f3f", (r"MiniMax", r"(?<![A-Za-z0-9])H3",)),
    ("SAMPLER", "#3f4759", (
        r"^Basic(Guider|Scheduler)$", r"^SamplerCustom", r"^KSampler")),
    ("OUTPUT", "#4a3f59", (
        r"^VAEDecode", r"^CreateVideo$", r"^Save", r"^Preview")),
)

GAP_X, GAP_Y = 80, 40          # between columns, and between nodes in one
PAD = 30                       # group box padding around its nodes
HEAD = 46                      # room for the group's own title bar
TOP = 120
MAX_H = 1400                   # a column taller than this wraps into a grid, the
                               # way the stock template lays its reference images


def column_of(cls):
    for i, (_, _, pats) in enumerate(COLUMNS):
        for p in pats:
            if re.search(p, cls):
                return i
    return None


def size_of(n):
    s = n.get("size") or [270, 100]
    if isinstance(s, dict):                       # older files use {"0":w,"1":h}
        s = [s.get("0", 270), s.get("1", 100)]
    return float(s[0]), float(s[1])


def layout(ui):
    """-> (ui, report). Assigns every node to a column and boxes each column."""
    nodes = ui.get("nodes") or []
    if not nodes:
        return ui, ["no nodes"]
    buckets, leftover = {}, []
    for n in nodes:
        c = column_of(n.get("type", ""))
        (buckets.setdefault(c, []) if c is not None else leftover).append(n)

    # widest node in a column decides that column's width, so nothing overlaps
    order = [i for i in range(len(COLUMNS)) if i in buckets]
    x = TOP
    groups, report = [], []
    for i in order:
        col = sorted(buckets[i], key=lambda n: n["id"])
        cw = max(size_of(n)[0] for n in col)
        cx, cy, used_w, bottom = x, TOP, cw, TOP
        for n in col:
            nh = size_of(n)[1]
            if cy > TOP and cy + nh > TOP + MAX_H:      # start a new sub-column
                cx += cw + GAP_X
                used_w = cx + cw - x
                cy = TOP
            n["pos"] = [cx, cy]
            cy += nh + GAP_Y
            bottom = max(bottom, cy - GAP_Y)
        title, colour, _ = COLUMNS[i]
        groups.append({"id": len(groups) + 1, "title": title,
                       "bounding": [x - PAD, TOP - PAD - HEAD,
                                    used_w + PAD * 2,
                                    (bottom - TOP) + PAD * 2 + HEAD],
                       "color": colour, "font_size": 24, "flags": {}})
        report.append("%-18s %2d node(s)%s" % (title, len(col),
                      "  (wrapped into %d columns)" % (1 + (used_w - cw) // (cw + GAP_X))
                      if used_w > cw else ""))
        x += used_w + PAD * 2 + GAP_X

    if leftover:
        y = TOP
        for n in sorted(leftover, key=lambda n: n["id"]):
            n["pos"] = [x, y]
            y += size_of(n)[1] + GAP_Y
        report.append("%-18s %d node(s) - no column matched, parked on the right"
                      % ("(ungrouped)", len(leftover)))
        for n in leftover:
            report.append("    %s %s" % (n["id"], n.get("type")))

    ui["groups"] = groups
    return ui, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    with open(a.workflow, encoding="utf-8") as fh:
        ui = json.load(fh)
    if "nodes" not in ui or "last_node_id" not in ui:
        sys.exit("that is not a UI workflow. Only the UI format has positions and "
                 "groups; an API-format graph has neither and cannot be laid out.\n"
                 "Save it from ComfyUI's menu (not Export API) and try again.")
    ui, report = layout(ui)
    out = a.out or a.workflow
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(ui, fh, indent=2)
    print("laid out    : %s" % out)
    for line in report:
        print("  %s" % line)


if __name__ == "__main__":
    main()

# Batch-importing a song folder into ComfyUI

A finished `songs/<name>/` holds three prompt files per scene - v1, v2, v3. For
Federphibien that is 51 scenes × 3 camera variants = 153 renders. This is how you
get them through ComfyUI without clicking 153 times.

## First, the honest part: core ComfyUI cannot do it

There is no combination of stock nodes that walks a folder of prompt files.

| what you need | core node | verdict |
|---|---|---|
| read a prompt from a `.txt` on disk | — | **no such node exists** |
| iterate an index | `PrimitiveInt` + `control_after_generate: increment` | works |
| loop a graph | — | no loop node in core |

So: use this kit's own `HurricaneSongFolder` node - one stdlib-only file, no
dependencies - which is what `README.md` describes and what the song folder is
built for. Option A below is the no-install path, and it is manual, one scene at
a time.

Whatever you pick, the reference-tag rule from `CLAUDE.md` still applies: H3
renumbers the tags over the slots you actually connected, so wire the loaders in
the order `__READ_ME.txt` lists them, from `ref_image_0`, leaving no gap. Load
the same slots for every scene of a set, or the tags written into the prompts
stop matching.

---

## What the deliverable gives you to work with

```
songs/Federphibien/
  set-NN_<sheets>/     one folder per set of reference sheets - the scenes that
                       need exactly those, and what renders them:
    NN_title-v1.txt      a finished six-section H3 prompt. Paste as-is.
    __SCENES.tsv         scene, frames, prompts, refs, title - one row per scene,
                         tab separated
    <song>-set-NN_*.json the render graph, yours with that set wired in
  __SCENES.tsv         the same, for the whole song, saying which set each scene
                       is in
  __TIMELINE.tsv       where each clip goes in the edit
  <song>-4x.json       the upscale pass afterwards
```

A set folder's `__SCENES.tsv` is the pairing, and `HurricaneSongFolder` reads it:
one prompt and one frame count per scene, one set per Run. That is the route these
folders are built for, and `README.md` describes it. What follows is what to do if
you will not install the node.

---

## Option A - manual, nothing to install

For one scene: open `NN_title-v1.txt`, paste the whole file into the H3 prompt
box (it is already six sections, no markup, nothing to strip), load that set's
reference images in the order `__READ_ME.txt` lists them, and set `length` to
243.

Never retype the length by feel. H3 only accepts lengths where
`frames % 17 == 5` and it silently rounds **up**, so a wrong number changes the
clip duration and every timecode in `__TIMELINE.tsv` is off.

---

## After rendering

ComfyUI writes the clips to its output folder. Join them in filename order:

```bash
./mvkit concat /path/to/ComfyUI/output/set-01_2-5
```

Then take it into DaVinci: lay the song under the picture, place each clip at the
timecode `__TIMELINE.tsv` gives it, trim the tail (every render is 10.125 s and
most beats are shorter), cut between the v1/v2/v3 coverage inside a scene, and
add the period grade there - never in the prompt.

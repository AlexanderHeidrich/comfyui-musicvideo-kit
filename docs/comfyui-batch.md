# Batch-importing a song folder into ComfyUI

A finished `songs/<name>/` holds one prompt file and one audio slice per scene.
For Federphibien that is 49 scenes × 3 camera variants = 147 renders. This is
how you get them through ComfyUI without clicking 147 times.

## First, the honest part: core ComfyUI cannot do it

There is no combination of stock nodes that walks a folder of text + audio.

| what you need | core node | verdict |
|---|---|---|
| read a prompt from a `.txt` on disk | — | **no such node exists** |
| load audio from an arbitrary path | `LoadAudio` | only files already in `ComfyUI/input`, chosen from a dropdown, no path input, no batching |
| iterate an index | `PrimitiveInt` + `control_after_generate: increment` | works |
| loop a graph | — | no loop node in core |

So: use this kit's own `HurricaneSongFolder` node - one stdlib-only file, no
dependencies - which is what `README.md` describes and what the song folder is
built for. Option A below is the no-install path, and it is manual, one scene at
a time.

Whatever you pick, the reference-tag rule from `CLAUDE.md` still applies: H3
renumbers `<Picture n>` / `<Video n>` / `<Audio n>` over the slots you actually
connected, and a reference video's own soundtrack claims an `<Audio>` number
before any standalone audio. Load the same slots for every scene of a song, or
the tags written into the prompts stop matching.

---

## What the deliverable gives you to work with

```
songs/Federphibien/
  set-NN_<sheets>/     one folder per set of reference sheets - the scenes that
                       need exactly those, and what renders them:
    NN_title-v1.txt      a finished six-section H3 prompt. Paste as-is.
    NN_title.mp3         the audio slice for that scene, shared by v1/v2/v3
    __SCENES.tsv         scene, start, end, frames, duration, inner_cut, audio,
                         prompts, refs, lyrics - one row per scene, tab separated
    <song>-set-NN_*.json the render graph, yours with that set wired in
  __SCENES.tsv         the same, for the whole song, saying which set each scene
                       is in
  <song>-4x.json       the upscale pass afterwards
```

A set folder's `__SCENES.tsv` is the pairing, and `HurricaneSongFolder` reads it:
one prompt, one slice and one frame count per scene, one set per Run. That is the
route these folders are built for, and `README.md` describes it. What follows is
what to do if you will not install the node.

---

## Option A - manual, nothing to install

For one scene: open `NN_title-v1.txt`, paste the whole file into the H3 prompt
box (it is already six sections, no markup, nothing to strip), load
`NN_title.mp3` into the audio slot, load your reference image(s), and set
`length` to the `frames` value for that scene from `__SCENES.tsv`.

Never retype the length by feel. H3 only accepts lengths where
`frames % 17 == 5` and it silently rounds **up**, so a wrong number changes the
clip duration and the picture drifts off its own audio.

---

## After rendering

ComfyUI writes the clips to its output folder. Join them in filename order:

```bash
./mvkit concat /path/to/ComfyUI/output/video/MV
```

Then take it into DaVinci, trim the overlaps (screenplay mode deliberately makes
each clip a little longer than its scene), cut between the v1/v2/v3 coverage
inside a scene, and add the period grade there - never in the prompt.

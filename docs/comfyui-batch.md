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

So: either add two well-known node packs (option B), or drive ComfyUI from
outside over its HTTP API (option C). Option A is the no-install path for a
handful of scenes.

Whatever you pick, the reference-tag rule from `CLAUDE.md` still applies: H3
renumbers `<Picture n>` / `<Video n>` / `<Audio n>` over the slots you actually
connected, and a reference video's own soundtrack claims an `<Audio>` number
before any standalone audio. Load the same slots for every scene of a song, or
the tags written into the prompts stop matching.

---

## What the deliverable gives you to work with

```
songs/Federphibien/
  NN_title-v1.txt      a finished six-section H3 prompt. Paste as-is.
  NN_title.mp3         the audio slice for that scene, shared by v1/v2/v3
  __SCENES.tsv         scene, start, end, frames, duration, inner_cut, audio,
                       prompts, lyrics  - one row per scene, tab separated
  __batch/
    __README.txt       the group table: which length, how many queue runs
    f124-v1-prompts.txt   39 paths, one per line, relative to the song folder
    f124-v1-audio.txt     the same 39 scenes' mp3s, in the same order
    f158-v1-...           and so on, one pair per frame count
  ALL_scenes.txt       the same material in this kit's DSL, for mv_h3_nodes.py
```

The `__batch/` lists are grouped **by frame count** on purpose. H3's `length` is
a fixed widget, and only 5 distinct lengths occur across this song - 39 scenes
share 124 frames. So you set `length` once per group and queue that group, which
turns 147 renders into 15 queue runs.

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

## Option B - batch inside the graph (two node packs)

Install via ComfyUI Manager:

- **ComfyUI-VideoHelperSuite** (Kosinkadink) - for `Load Audio (Path)`
  (`VHS_LoadAudio`), which takes a path *string* instead of an input-dir
  dropdown, and reads mp3.
- **WAS Node Suite** (WASasquatch) - for `Text Load Line From File`
  (line N of a file, with `mode: index`) and `Load Text File` (a whole file's
  contents as a string).

### The graph

```
PrimitiveInt  "index"                        core
  value 0, control_after_generate: increment
        │
        ├──► Text Load Line From File        WAS
        │      file_path = __batch/f124-v1-prompts.txt
        │      mode = index,  index ◄── PrimitiveInt
        │            │
        │            └──► Load Text File     WAS
        │                   file_path ◄──────┘   (the line IS a path)
        │                        │
        │                        └──► prompt   ► MiniMax H3
        │
        └──► Text Load Line From File        WAS
               file_path = __batch/f124-v1-audio.txt
               mode = index,  index ◄── PrimitiveInt
                     │
                     └──► Load Audio (Path)   VHS
                            audio_file ◄──────┘
                                 │
                                 └──► audio    ► MiniMax H3

LoadImage  ► your character reference         ► MiniMax H3  (picture slot 1)
length = 124  (typed once, from __batch/__README.txt)
```

Two details that trip people up:

1. `file_path` on the WAS nodes is a widget. Drop a link onto it (or right-click
   the node → *Convert widget to input*) so the loaded line can drive it. That
   nesting - a list of paths, then a loader - is necessary because a prompt is
   multi-line and cannot live on one line of a list file.
2. `Load Audio (Path)` defaults its path to `input/`. The `__batch/` lists carry
   paths relative to the song folder, so the deliverable survives being copied to
   another machine - set the loader's base to wherever that folder now lives.

### Running it

For each row of `__batch/__README.txt`:

1. point both `Text Load Line From File` nodes at that group's `-prompts.txt`
   and `-audio.txt`,
2. set `length` to the group's frame count,
3. set `index` back to 0,
4. set the queue's **batch count** to the group's count and hit Run.

Fifteen passes for the whole song in all three camera variants. If you only want
the wide masters, the five `-v1` groups are enough: 49 renders.

---

## Option C - drive it over the API (recommended for a whole song)

ComfyUI serves an HTTP API on the same port as the UI. Queueing a job is one
POST to `/prompt` with the graph as JSON, so a loop outside ComfyUI does the
batching and needs no extra nodes at all. It also handles the per-scene frame
count without any grouping.

1. Build the graph once in the UI for a single scene and check that it renders.
2. Export it: **Workflow → Export (API)**. This is *not* the normal save - the
   API format is a flat map of node id → `{class_type, inputs}`, which is what
   `/prompt` accepts.
3. Give the three nodes you want driven a recognisable **title** (double-click
   the title bar): `PROMPT`, `AUDIO`, `LENGTH`.
4. Loop:

```bash
bin/queue_comfy.py songs/Federphibien workflow_api.json --variant v1
bin/queue_comfy.py songs/Federphibien workflow_api.json --variant v1 --dry-run   # inspect first
```

`queue_comfy.py` reads `__SCENES.tsv`, substitutes each scene's prompt text,
audio path and frame count into the nodes you titled, and POSTs one job per
scene. It is stdlib-only. `--dry-run` prints what it would send and posts
nothing - use it first, because it also tells you whether it found your titled
nodes.

Options: `--host` (default `http://127.0.0.1:8188`), `--variant` (v1/v2/v3),
`--scenes 1-10,15` to queue a subset, `--title-prompt/-audio/-length` if you
titled the nodes differently.

---

## After rendering

ComfyUI writes the clips to its output folder. Join them in filename order:

```bash
./mvkit concat /path/to/ComfyUI/output/video/MV
```

Then take it into DaVinci, trim the overlaps (screenplay mode deliberately makes
each clip a little longer than its scene), cut between the v1/v2/v3 coverage
inside a scene, and add the period grade there - never in the prompt.

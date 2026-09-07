# MusicVideoKit

Turns a song and its screenplay into per-scene storyboards for **MiniMax H3
reference-to-video** in ComfyUI, and tells you where each rendered clip goes on
the timeline.

**An agent writes the prompts; the scripts only file them.** There is no
template merger and no drafting model in the loop. The prompts live as frozen
full text in `songs/<name>/_source/scenes.json`, written by
[`.claude/skills/storyboard/`](.claude/skills/storyboard/) - a committed Claude
Code skill that runs the whole job; say "storyboard this song". `mvkit pack`
files that JSON into a deliverable and refuses to ship a prompt that breaks a
documented H3 limit.

`CLAUDE.md` is the playbook for agents (`AGENTS.md` is the same file) and is the
authority on H3's constraints. Read it before changing anything about quality.

Runs on macOS, Linux and Windows. Everything but `concat` needs nothing but
python3; `concat` needs ffmpeg. Or install nothing and let Docker do it.

```bash
./mvkit doctor          # what you have, and which engine will be used
```

---

## One entry point

```
./mvkit <command>

new       <name> <audio>   scaffold songs/<name>
drehbuch  <song>           _source/*.pdf -> _source/drehbuch.txt
pack      <song>           _source/scenes.json -> the set-*/ deliverable
workflows <song> [--from saved.json]   one grafted render graph per set
layout    <song> [wf.json] re-lay-out a graph that lost its layout
probe                      ask a running ComfyUI which nodes it has
concat    <dir> [out]      join rendered clips
doctor                     what is installed
```

Windows without Git Bash: `mvkit.cmd <command>` (identical, via Docker).

---

## Worked example: a full song, start to finish

The song is 2:47 with a 51-scene screenplay in a Google Docs PDF.

### 1. Scaffold

```bash
./mvkit new federphibien /tmp/federphibien.mp3
```

Creates the input slots under `songs/federphibien/_source/` and an empty
`refs/` with the naming schema in it.

### 2. Drop in the screenplay and the reference sheets

```bash
cp ~/Downloads/Federphibien.pdf songs/federphibien/_source/
./mvkit drehbuch federphibien          # pdf -> _source/drehbuch.txt, stdlib only
cp ~/art/*.png  songs/federphibien/refs/
```

The filename decides what a sheet **is** and in which order H3 loads it:

| pattern | is |
|---|---|
| `NN_char_<slug>.png` | a character |
| `NN_loc_<slug>.png` | a location or set |
| `NN_prop_<slug>.png` | a prop |
| `NN_style_<slug>.png` | a look / colour board |

`NN` sets the load order, which is what makes the tag numbering deterministic.
**Every sheet becomes a `<Subject n>` in the prompt, never a `<Picture n>`** -
per MiniMax's own spec a `<Picture n>` entry is a *concrete target frame*, so
writing a location that way is how you order it as frame one. That mistake put a
pond in the first frame of a hen-house scene once. Limits: 9 images, 3 videos,
12 media in total, and audio-only input is rejected.

**No sheet may look like a frame.** A character sheet is a **turnaround** -
front, side, back, top on one image; a single front portrait is why "from
behind" never worked, because H3 had never seen the frog's back. A location
sheet is an **element board** - the water, the fence, the coop, the palette as
separate studies on bare paper - never a finished background painting. A
finished painting is one viewpoint, so every other angle gets invented, and in
16:9 it is indistinguishable from a first frame.

The sheets are also the **style authority**. When a sheet and a written
description disagree, the sheet is right and the description gets corrected.

### 3. Write the prompts

That is the agent's job, not a script's: `.claude/skills/storyboard/SKILL.md`
reads `drehbuch.txt`, the sheets and `_source/brief.txt`, and writes
`_source/scenes.json` - one entry per scene with its screenplay frame range
(`beat`), its sheets, and the full text of v1/v2/v3.

### 4. Pack, and graft the graphs

```bash
./mvkit pack      federphibien
./mvkit workflows federphibien          # --from <saved.json> the first time
```

`pack` groups the scenes by the set of sheets they need, numbers those sheets the
way H3 will, writes the set folders, `__READ_ME.txt` and `__TIMELINE.tsv`, and
**fails** on a prompt over 7,000 characters rather than truncating it - a
truncating script would cut the shot off the end, which is the failure the limit
exists to avoid. Read its warnings; they are the honest report of what it found.

A pack rewrites the set folders from scratch, so `workflows` runs after it. Never
hand-edit a generated file - edit `scenes.json` and pack again.

---

## What a finished song folder holds

```
songs/federphibien/
  __READ_ME.txt        what this folder is: the work list and the loader order
  __SCENES.tsv         scene -> set, title, location, sheets
  __TIMELINE.tsv       the edit list: timecode, how long it holds, track, render
  set-NN_<sheets>/     one folder per set of reference sheets, self-contained:
    NN_title-v1.txt      a paste-ready six-section H3 prompt
    NN_title-v2.txt      same action, different camera
    NN_title-v3.txt      same action, close/detail
    __SCENES.tsv         what HurricaneSongFolder reads
    <song>-set-NN_*.json the graph, carrying only that set's sheets
  <song>-4x.json       the upscale pass afterwards
  refs/                the sheets - the one input you wire in by hand
  _source/             every input; nothing here is meant to be copied out
```

There is **no audio anywhere in the deliverable**. The song goes under the
picture in the edit.

---

## What H3 pins down

The authority is MiniMax's own spec (`references/ref-en.txt` and `base-en.txt` in
`MiniMax-AI/MiniMax-H3`), not a blog. `CLAUDE.md` carries the full list; the ones
that shape the whole kit:

- **The frame grid.** `length` is valid only where `frames % 17 == 5`, trained
  range 124-362, and H3 rounds up. This kit uses **243 frames = 10.125 s for
  every scene**; the node's length is set once and never touched. Max ~15 s per
  generation, so one scene is one render.
- **Reference tags renumber** over the slots actually connected, so a gap shifts
  every tag after it. Wire the loaders in the order `__READ_ME.txt` lists them,
  from `ref_image_0`, leaving no gap.
- **Six sections in order**, `subject_definitions` first, `non_diegetic_music`
  last, with a bracketed task type opening the `summary`.
- **Camera moves are natural English from a closed vocabulary** - Zoom In/Out,
  Push In/Pull Out, Pan, Truck, Tilt, Pedestal, Arc Shot, Tracking Shot, Static
  Shot, Shake, POV, Roll - with only `with small/large amplitude` and
  `at slow/fast speed` as modifiers. Square-bracket moves are Hailuo 02 grammar,
  not H3's. One dominant move per clip. There is no negative prompt.
- **Scale is not in the references.** Every sheet is its own frame, so H3 has
  nothing to size characters by: every subject block carries real measurements.

**Reference audio is not playback.** H3 re-sings the prompt's own words in the
supplied clip's voice at a timing it invents, which is why feeding it a slice of
the song under a printed lyric produced clips singing the wrong words. There is
now no audio reference anywhere and nothing in the film moves a mouth, so nothing
can be out of sync.

**A reference not in the shot must not be connected.** Words do not undo a
connected picture: with all sheets wired, a scene saying "do not use
`<Picture 5>`" still got it as its first frame. Presence is declared per scene in
`scenes.json`, never guessed from keywords, and because a saved graph cannot
change how many links it has, `pack` groups the scenes by their sheet tuple so
each graph connects exactly what its scenes contain.

---

## What is in a scene

`NN_slug-v1/-v2/-v3.txt` are **coverage of one moment, not alternative scenes**:
v1 wide master, v2 alternative angle, v3 close/detail. The `summary` and the
action are byte-identical across all three; only the camera sentence differs, so
they cut together inside one scene. The set graphs pin `RandomNoise` to `fixed`
so all three start from the same noise.

Two consequences `pack` lints for: neither the summary nor the action may name a
framing, or it contradicts two of the three variants; and a scene must state its
location before `[Shot 1]`, because a prompt with no stated location invents one
and the style block decides which.

A beat shorter than 5 s is not stretched - it gets a **second setup of the same
moment** as an internal cut at 00:05.000. Two angles inside one generation are
the same render, so the place cannot drift between them; that is also the answer
to continuity, since two separate renders share nothing but the sheets. For a
hard match across a cut, feed the last frame of one clip in as the first frame of
the next and switch that prompt to `[keyframe completion]`.

---

## Getting it into ComfyUI

The `NN_title-vN.txt` files are **finished H3 prompts** - six sections, no
markup, nothing to strip. Paste one in exactly as it is.

**The kit does not invent a render graph.** `MiniMaxH3ReferenceToVideo` returns
`positive` and `LATENT` - it conditions a sampler and hands back no video - so a
working graph needs a UNET loader, CLIP and VAE loaders, a sampler, a VAEDecode
*and* a VAEDecodeAudio, and a CreateVideo behind it. ComfyUI ships that chain
under **Workflow → Browse Templates**. Get it rendering one scene, save it, and
hand it over:

```bash
./mvkit workflows federphibien --from video_minimax_h3_ref2va.json
```

Hand it the workflow **saved** from the menu, not an API export: the graft edits
that format in place, so your layout, groups, sampler, scheduler, LoRA switches,
resolution and Save node all survive. Only `prompt`, `length`, the Save node's
`filename_prefix` and the `ref_images.ref_image_*` slots are rewired, the loaders
a set does not need are removed, and the rest are retitled with their live tag.
The graph is kept as `_source/workflow.json` and every `workflows` run re-grafts
from it.

It also sets two defaults the stock template ships the wrong way round:
`RandomNoise` to `fixed`, because a fresh seed is the one variable that should not
move between v1/v2/v3, and the Lightning LoRA boolean to `True`, because the
4-step turbo LoRA is wired in and shipping it off renders the slow path.

**No absolute paths are written.** ComfyUI usually runs on another machine, so
`song_path` is left empty and the build refuses to emit a graph carrying one.
For the same reason the sheets are named by bare filename - which means
**`LoadImage` only reads `ComfyUI/input/`, so copy `refs/*.png` in there by hand**
or every loader comes up empty.

**The nodes** live in [comfyui/custom_nodes/](comfyui/custom_nodes/) - the path
mirrors where they go. Two independent files, stdlib only:

| file | node |
|---|---|
| `watching_hurricanes.py` | Hurricane Song Folder |
| `watching_hurricanes_upscale.py` | Hurricane Clip Folder |

**The installed node has to be the kit's node.** The graphs wire its outputs by
index, so an older copy shifts every link past the change: dropping `audio_path`
once moved `frames` to slot 1, so `length` was fed a STRING and the renders were
named after a number. `./mvkit probe` compares a running server's sockets against
the node file and says so.

**One set at a time.** Point `song_path` at `set-NN_.../`, set the control beside
`scene_index` to `increment`, set the queue's **Batch count** to that folder's
`scene_count`, press Run once, move to the next folder. `__READ_ME.txt` carries
the work list and the loader order. A batch count set too high raises rather than
silently re-rendering the last scene.

**Where the clips land.** Save Video writes to `ComfyUI/output` and stays; it is
Preview nodes that write to `temp` and get cleared. `save_prefix` is wired into
`filename_prefix`, so clips arrive as `output/set-NN_x/NN_slug-vN_00001_.mp4` -
named after the prompt that made them, which is what `__TIMELINE.tsv` and
`mvkit concat` read.

**[docs/comfyui-batch.md](docs/comfyui-batch.md)** shows why stock ComfyUI is not
enough on its own, and how to render a scene by hand if you will not install the
node.

---

## Where each clip goes in the edit

`__TIMELINE.tsv` is the edit list, one row per scene:

```
scene  tc           start_s  dur_s   track  set         render
2      00:00:10:00  10.000   6.458   V1     set-01_2-5  set-01_2-5/02_the-drone-descends-v1
19     00:01:05:17  65.708   5.750   V2     set-10_1-3  set-10_1-3/19_the-hen-crocheting-v1
```

It is laid out at **24 fps** - the basis the screenplay itself names - off the
Drehbuch's own frame numbers, starting from the earliest beat. A Vorspann written
as `Frame -240 bis 0` therefore fills the head of the timeline, and
`__READ_ME.txt` says the one timecode you need: **where to drop the mp3** so
everything lines up.

- `dur_s` is how long the scene **holds**, not how long the clip is. Every render
  is 10.125 s and most beats are shorter, so trim rather than stretch. `pack`
  warns where a beat is *longer* than its render and has to be looped or held.
- `track` is `V2` where a beat sits inside a longer one. That is a layer, not a
  cut - a half-transparent daydream over a looping hop - so it gets its own
  track above the plate. Nothing is ever burned into a render; the assembly
  happens in DaVinci.
- `render` is the filename prefix ComfyUI writes, before its own counter.

---

## Upscale, once you have thrown out the bad takes

`<song>-4x.json` is a separate graph with **no H3 in it**. Point Hurricane Clip
Folder at the folder you pruned by hand - it lists what is *actually* there, so a
take you deleted is simply not in the run - set `clip_index` to `increment` and
the batch count to `clip_count`, and leave it overnight.

```
Hurricane Clip Folder ─► Load Video (Path) ─► Upscale 4x ─► Video Combine
 (source_dir)                    └─ audio ───────────────────┘
```

One 4x line-art model and **nothing after it** - the output is exactly 4x the
render. Only a 540p source lands on 4K on the nose; correct the rest in the edit,
which scales better than a second model pass.

Deliberately not a diffusion upscaler. A picture made of an ink line and flat
washes has no hidden detail to reconstruct, so a generative model invents texture
in fills that must stay flat - and invents it differently in every frame, which
shimmers far more on flat colour than on photographic footage. ESRGAN-class
models are deterministic, so they are temporally stable for free.

The model, exactly: **`RealESRGAN_x4plus_anime_6B.pth`** (17 MB), from
[the Real-ESRGAN v0.2.2.4 release](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth).
It goes in `<your ComfyUI>/models/upscale_models/` and needs a browser refresh
before the dropdown sees it - that list is built when the UI loads. `.pth` is
fine as-is, no conversion. Clips keep their own names, so the pairing with the
prompt survives the pass.

## Join the clips

```bash
./mvkit concat /path/to/ComfyUI/output/set-01_2-5
```

Concatenates every `.mp4` in the directory in filename order with `-c copy`, and
reports the duration it actually got.

---

## The screenplay format

`_source/drehbuch.txt` is the whole timing model: one scene per `Frame <a> bis
<b>` block, one to one, each rendered as 243 frames. A block naming several
distinct actions ("Mehrere Cuts", two things happening) becomes two scenes.
Quoted text in a block is a lyric and does **not** go into the prompt.

```
Grundlage für das Drehbuch sind 24 FPS
------------------------------------------------------------------
Frame 446 bis 508
"Ich sitze traurig am Rand vom Teich"        <- quoted text is the lyric
Closeup auf das Gesicht des Frosches.        <- the rest is the action
Glasiger Blick, Wolken spiegeln sich.
```

`mvkit drehbuch` extracts that from a PDF with the stdlib only - no poppler, no
pip. The document's fps only converts frame numbers to seconds; H3 itself always
renders at 24 fps, which is fixed by its frame grid.

---

## Docker, make, Windows

| | |
|---|---|
| `./mvkit <cmd>` | native if python3 is on PATH, else Docker |
| `./mvkit --docker <cmd>` | force Docker |
| `mvkit.cmd <cmd>` | Windows, always Docker |
| `make check` | syntax-check every script |
| `docker compose build` | build the image |
| `docker compose run --rm mvkit bash` | a shell in it |

The repo is bind-mounted, so edits take effect without a rebuild.

---

## Known limitations

- Claude cannot read pre-existing files in `~/Downloads` on macOS (TCC). Copy the
  file elsewhere or grant Full Disk Access.
- Scanned PDFs have no text layer, so `mvkit drehbuch` comes back empty. Write
  `drehbuch.txt` by hand.
- `ffprobe` reports container length, not music: Federphibien's mp3 is 207.2 s
  but the music ends at ~167 s and the rest is digital silence. Measure with
  `volumedetect` before believing a duration.
- The ComfyUI nodes' parsing and tag logic is tested standalone. Two
  VideoHelperSuite connections in the upscale graph want one look in the UI,
  because VHS has renamed both between versions.
- `mvkit new`, the `templates/` tree, most `Makefile` targets and the Dockerfile's
  whisper build are left over from the pipeline that generated prompts from
  templates. They are not part of the current job and are not maintained.

## Grade artefacts stay out of the prompt

The `[style]` block explicitly forbids grain, video noise, VHS softness,
scanlines, chroma bleed, gate weave, dust, halation and lens effects. The prompt
describes the *craft* instead - how the line was drawn, how the paint was laid,
animation on twos, rostrum camera - never the condition of an old tape. The
period damage goes on afterwards in DaVinci, where you can still take it off. It
is also what makes the upscale pass work: a clean plate upscales, a grainy one
amplifies its grain.

For a 90s broadcast grade, the artefacts that actually read are composite video
ones: chroma bleed and dot crawl, slight horizontal smear, interlace combing on
motion, head-switching noise along the bottom edge, occasional tape dropout, a
little vertical jitter, and clipped NTSC/PAL saturation.

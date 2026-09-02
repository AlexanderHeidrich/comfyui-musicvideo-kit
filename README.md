# MusicVideoKit

Turns a song into per-scene storyboards for **MiniMax H3 reference-to-video** in
ComfyUI. Timings come from the actual audio and, when you have one, from your
screenplay - so the cuts sit on the lyrics instead of on a metronome.

Runs on **macOS, Linux and Windows**. Either install ffmpeg + whisper.cpp
natively, or install nothing and let Docker do it.

```bash
./mvkit doctor          # what you have, and which engine will be used
```

`CLAUDE.md` is the playbook for agents (`AGENTS.md` is the same file), and
`.claude/skills/storyboard/` is a committed Claude Code skill that runs the
whole intake and wiring for you - just say "storyboard this song".

---

## Quick start

```bash
./mvkit new mysong ~/Music/mysong.mp3 90s-cartoon-dirty
cp ~/Downloads/Drehbuch.pdf songs/mysong/_source/     # optional, but do it
cp ~/refs/*.png            songs/mysong/_source/refs/ # see refs/__README.txt
./mvkit all mysong
```

That produces `songs/mysong/` - flat, paired, ready to paste into ComfyUI - and
`songs/mysong/__READ_ME.txt` explaining it.

Windows without Git Bash: use `mvkit.cmd all mysong` (identical, via Docker).
Prefer make? `make all SONG=mysong`.

---

## Worked example: a full song, start to finish

The song is 2:47 with a 50-scene screenplay in a Google Docs PDF.

### 1. Scaffold

```bash
./mvkit new federphibien /tmp/federphibien.mp3 90s-cartoon-dirty
```

Creates every input slot:

```
songs/federphibien/_source/
  song.mp3              your track
  brief.txt             [style], [sound], [music] and one [subject] per
                        reference - the only thing the prompts are built from
  style_examples.txt    free notes: "like Ren & Stimpy but rougher"
  tail.txt              audio fallback, used where brief.txt is silent
  lyrics.txt            the real lyrics, optionally [mm:ss] prefixed
  content.json          {}
  refs/__README.txt     the reference naming schema
```

### 2. Drop in the screenplay and the references

Not sure which references to make? `./mvkit shotlist <song>` reads `brief.txt`
and writes `_source/refs/__SHOTLIST.txt`: which images are worth
generating for this song, ranked by how many scenes each character is actually
in, with a ready-to-paste prompt for each built from the film's own style block.

```bash
cp ~/Downloads/Federphibien.pdf songs/federphibien/_source/
cp ~/art/federphibium.png       songs/federphibien/_source/refs/01_char_federphibium.png
cp ~/art/pond.png               songs/federphibien/_source/refs/02_loc_pond.png
```

Reference filenames carry their meaning and their load order:

| pattern | is | gets |
|---|---|---|
| `[NN_]char_<slug>.png` | a character | `<Picture n>` |
| `[NN_]style_<slug>.png` | a look / colour board | `<Picture n>` |
| `[NN_]loc_<slug>.png` | a location | `<Picture n>` |
| `[NN_]prop_<slug>.png` | a prop | `<Picture n>` |
| `[NN_]video_<slug>.mp4` | a motion reference | `<Video n>` |

### 3. Run it

```bash
./mvkit all federphibien
```

which is these steps, each also runnable alone:

```bash
./mvkit drehbuch   federphibien   # _source/*.pdf     -> _source/drehbuch.txt
./mvkit transcribe federphibien   # song.mp3          -> transcript.json/.tsv/.txt
./mvkit scenes     federphibien   # drehbuch+transcript -> scenes.tsv
./mvkit refs       federphibien   # refs/            -> refs.json + the H3 tags
./mvkit split      federphibien   # song.mp3         -> scene_NN.mp3
./mvkit draft      federphibien   # screenplay+lyrics -> content.json
./mvkit build      federphibien   # everything       -> the flat NN_*.txt files
./mvkit verify     federphibien   # measures the timing rather than trusting it
```

Real output from the scenes step on this song:

```
drehbuch: 50 scenes, frame numbers read at 24 fps (H3 renders at 24 fps)
scenes            : 48 (incl. scene 0, no audio)
covers           : 0.000 -> 171.417 s  (song 207.203 s, -35.786)
durations        : 5.167 .. 12.250 s  (all on the 17k+5 grid: True)
longest tail     : +0.667 s of clip past its scene, trim in the edit
! 1 scene(s) end before the music starts - kept as scene 0, 5.167s with no audio
! scenes at 46.75s..55.71s are one held setup - fused, with 2 internal cut(s)
! 36 scene(s) were shorter than H3's 5.17s minimum - padded, so they overlap
```

Read those warnings. They are the honest report of what H3 could not do.

**Two time bases, on purpose.** `__SCENES.tsv` carries `song_start`/`song_end` -
the window of the track a clip takes its audio from - and `tl_frame`, the frame
the clip sits on in the edit. A screenplay block that ends before the music
starts becomes **scene 00**, a clip with no audio at all, and everything after it
shifts on the timeline without moving on the song. Scene numbers **90 and up** are
compositing elements: clips that exist only to be laid over something, so they
have no audio and no place on the timeline either.

### 4. Write the prose, rebuild

`draft` seeds `content.json` from the screenplay so the folder already renders.
Then improve it - by hand, with Claude (`.claude/skills/storyboard/`), or with a
local model:

```bash
./mvkit llm-up                       # ollama + gemma3:4b in Docker, ~3 GB, once
./mvkit draft federphibien --llm     # rewrites content.json into shot language
./mvkit build federphibien
```

Edit `_source/brief.txt` and `_source/content.json` - never the generated
files - and re-run `build`.

### 5. Get it into ComfyUI

The `NN_title-vN.txt` files are **finished H3 prompts** - MiniMax's six sections,
no markup, nothing to strip. Paste one in exactly as it is.

One scene = one H3 render, so a whole song is one render per scene per camera
variant. Two workflows live in the song folder:

```
__workflow_song.json     the render - YOUR H3 graph with the folder wired in
__workflow_upscale.json  the pass afterwards, no H3 in it
```

**The kit does not invent a render graph.** `MiniMaxH3ReferenceToVideo` returns
`positive` and `LATENT` - it conditions a sampler and hands back no video - so a
working graph needs a UNET loader, CLIP and VAE loaders, a sampler, a VAEDecode
*and* a VAEDecodeAudio, and a CreateVideo behind it. ComfyUI ships that whole
chain under **Workflow → Browse Templates**. Get it rendering one scene, save it,
and hand it over:

```bash
./mvkit workflows federphibien --from video_minimax_h3_ref2va.json
```

Hand it the workflow **saved** from the menu, not an API export: the graft edits
that format in place so your layout and groups survive, and it is the file you
open again to render. Everything you set stays: loaders, sampler, scheduler, LoRA
switches, resolution, the audio decode path, your Save node. Only four things are
rewired - `prompt`, `length`, `ref_audios.ref_audio_0` and the
`ref_images.ref_image_*` slots - each reference loader **titled with its live
tag**, so the graph says which image is `<Picture 3>`. Your Save node's
`filename_prefix` gets driven from `save_prefix`.

Connect as many `ref_image` slots as you have sheets *before* exporting: they are
dynamic, and a node with one slot takes one sheet. It warns rather than pretending.

**No absolute paths are written.** ComfyUI usually runs on another machine, so
`song_path` is left empty and the node title says to set it; the build refuses to
write a graph that carries one.

**The nodes** live in [comfyui/custom_nodes/](comfyui/custom_nodes/) - the path
mirrors where they go. Two independent files, stdlib only:

| file | nodes |
|---|---|
| `watching_hurricanes.py` | Song Folder |
| `watching_hurricanes_upscale.py` | Clip Folder |

`./mvkit probe` asks a running server what it has and what to title what - useful
after a node-pack update, not needed for the normal job.

**Running the whole song is one press of Run.** Set `song_path`, set the control
beside `scene_index` to `increment`, set the queue's **Batch count** to the number
of scenes (the data rows in `__SCENES.tsv`), and press Run once - ComfyUI queues
that many jobs and steps the index for you. Nothing to click in between. A batch
count set too high raises rather than silently re-rendering the last scene.

The reference sheets are not driven per scene, because they are identical in every
scene: their loaders keep their own filenames and are only retitled with their
live tag. Only the prompt, the frame count and the audio slice change.

**Where the clips land.** Renders are not temporary - Save Video writes to
`ComfyUI/output` and stays; it is Preview nodes that write to `temp` and get
cleared. Hurricane Song Folder has a `save_prefix` output wired into
`filename_prefix`, so clips arrive as
`output/<song>/NN_slug-vN_00001.mp4` - grouped per song and named after the
prompt that made them, which is what `mvkit concat` reads.

**[docs/comfyui-batch.md](docs/comfyui-batch.md)** shows why stock ComfyUI is not
enough on its own, and how to render a scene by hand if you will not install the
node.

### 5b. Check the timing

```bash
./mvkit verify Federphibien
```

Measures the frame grid, the arithmetic and the audio: every slice's decoded
length against what it claims, and where it actually sits in the song. Nothing
downstream survives a wrong `scenes.tsv`, so this is worth running after any
change.

### 6. Upscale, once you have thrown out the bad takes

`__workflow_upscale.json` is a separate graph with **no H3 in it**. Point Hurricane
Clip Folder at the folder you pruned by hand - it lists what is *actually* there,
so a take you deleted is simply not in the run - set `clip_index` to `increment`
and the batch count to `clip_count`, and leave it overnight.

```
Hurricane Clip Folder ─► Load Video (Path) ─► Upscale 4x ─► Video Combine
 (source_dir)                    └─ audio ───────────────────┘
```

One 4x line-art model and **nothing after it** -
the output is exactly 4x the render. Only a 540p source lands on 4K on the nose;
correct the rest in the edit, which scales better than a second model pass.

Deliberately not a diffusion upscaler. A picture made of a black ink line and
flat washes has no hidden detail to reconstruct, so a generative model invents
texture in fills that must stay flat - and invents it differently in every frame,
which shimmers far more on flat colour than on photographic footage. ESRGAN-class
models are deterministic, so they are temporally stable for free.

The model, exactly: **`RealESRGAN_x4plus_anime_6B.pth`** (17 MB), from
[the Real-ESRGAN v0.2.2.4 release](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth).
It goes in `<your ComfyUI>/models/upscale_models/` and needs a browser refresh
before the dropdown sees it - that list is built when the UI loads. The graph
already names the file, so `Load Upscale Model` (`UpscaleModelLoader`) and
`Upscale Image (using Model)` (`ImageUpscaleWithModel`) resolve on their own once
it is there. `.pth` is fine as-is, no conversion.

Clips keep their own names, so the pairing with the prompt survives the pass.

### 7. Join the clips

```bash
./mvkit concat ComfyUI/output/video/MV
```

---

## The screenplay format

`_source/drehbuch.txt` is the timing spine. `mvkit drehbuch` extracts it from a
PDF (stdlib only - no poppler, no pip), keeping headings as separators. You can
also write it by hand. One block per scene:

```
Grundlage für das Drehbuch sind 24 FPS       <- fps is read from text like this
                                                (or a "# fps: 25" line)
------------------------------------------------------------------
Frame 446 bis 508
"Ich sitze traurig am Rand vom Teich"        <- quoted text is the lyric
Closeup auf das Gesicht des Frosches.        <- the rest is the action
Glasiger Blick, Wolken spiegeln sich.
```

Accepted range forms: `Frame 446 bis 508`, `Frame 446-508`,
`00:18.583-00:21.167 | title | description`, and `f446-f508`.

The document's FPS only converts frame numbers to seconds. H3 itself always
renders at 24 fps - that is fixed by its frame grid.

### Why scenes overlap instead of drift

H3 accepts a clip length only where `frames % 17 == 5`, and it **rounds up**.
Ask for 5.20 s and you get 5.875 s.

- **With a screenplay**, every scene is anchored to its own start frame and its
  length is rounded **up** to the grid. Each clip therefore always covers its
  scene and carries a small tail into the next one. Picture stays on the lyric;
  you trim the tail in the edit. Scenes shorter than H3's 5.167 s minimum are
  padded (they overlap more); scenes longer than 15.083 s are split into parts.
- **Without a screenplay** (`--uniform 10`, `--at`, `--sections`), scenes are
  laid end to end, so there is no cumulative drift at all and the audio slice
  and the clip are the same length by construction.

---

## Continuity when there are no reference images

`First Frame <> Last Frame` in the screenplay means one unbroken camera setup.
`mvkit scenes` finds those runs and, when a run fits inside a single generation,
fuses it into one scene with internal cuts instead of several overlapping ones -
on Federphibien three held scenes totalling 8.96 s became one 9.42 s render.
What cannot be fused is reported in `__READ_ME.txt` as a chain: render those in
order and feed the previous clip's last frame in as the next one's first frame.
`__SCENES.tsv` carries it in a `continuity` column (`hold`, `chain`).

## What a finished song folder holds

```
songs/federphibien/
  __READ_ME.txt        what this folder is, in plain language, including a
                       synopsis of the screenplay and how to render the folder
  __SCENES.tsv         scene, song_start, song_end, tl_frame, frames, duration,
                       inner_cuts, continuity, audio, prompts, lyrics
  NN_title-v1.txt      a paste-ready six-section H3 prompt
  NN_title.mp3         the audio slice, shared by v1/v2/v3
  <song>.json          the render graph - yours, with this folder grafted in
  <song>-4x.json       the upscale pass afterwards, regenerated on every build
  _source/             every input; nothing here is meant to be copied out
```

`__READ_ME.txt` is generated but its prose is not: `_source/synopsis.txt` is
written by hand (or by an agent that read the screenplay) and baked in, and the
build only warns when `drehbuch.txt` is newer than it. A script summarising prose
could reword it but never check whether the reading is right.

**Compositing is listed, not baked.** Where the screenplay asks for something laid
over something else - a half-transparent hen in the sky, three daydreams over a
looping hop - the plate is rendered with that area deliberately EMPTY and the
overlay is a full-frame clip of its own. `__READ_ME.txt` gets a COMPOSITING
section naming which file is a plate, which is an inset or element, what loops and
what freezes. Nothing is burned into a render, because the assembly happens in
DaVinci.

## What is in a scene

`NN_..-v1/-v2/-v3.txt` are **coverage, not alternatives**: the same action from
three cameras. **v1 is whatever the screenplay asked for** - `mvkit scenes`
pulls the framing out of the Drehbuch and the build warns if v1 ignores it - and
v2/v3 cover it by film-theory practice (never repeat v1's size, cross the axis,
let one carry what the master cannot). See
[templates/cameras/__COVERAGE.txt](templates/cameras/__COVERAGE.txt).
Without a screenplay it falls back to a generic wide / angle / detail set. The ACTION text
is byte-identical in all three; only the camera block differs. All three share
the one `NN_...mp3`. Render two or three and cut between them inside the scene.

Two consequences the build lints for: the action must not name a framing, or it
contradicts two of the three variants; and descriptions are written in English
whatever language the screenplay is in, because H3 follows English shot language
far better. Lyrics and dialogue stay verbatim in their original language.

Where the scene is long enough, it also carries an internal cut placing a
**Shot 2 of harvestable B-roll**, snapped to a real ASR segment boundary so it
never lands mid-word. `scenes.tsv` reports whether that snap succeeded.

---

## Everything you can tune without touching code

```
templates/
  __README.txt          what each file does
  cameras.txt           the active camera set (v1/v2/v3 blocks)
  sections.txt          H3's six prompt sections and what belongs in each
  drafting.txt          the brief used when content.json is written
  comfyui.txt           the render instructions baked into every song's README
  cameras/              camera sets to pick from - drop one over cameras.txt
    __GLOSSARY.txt      shot sizes, angles, moves, amplitude and speed
    static-coverage.txt  moving-coverage.txt  rostrum-2d.txt
    handheld-doc.txt     anime-drama.txt
  styles/               look blocks: 90s-cartoon-dirty.txt, _TEMPLATE.txt
  tail/                 the audio fallback skeleton
```

Any song may override `cameras.txt`, `sections.txt` or `drafting.txt` by placing
its own copy in `songs/<name>/_source/`. Lines starting with `#` are comments and
are stripped before the text reaches the model - which is where show names and
other references belong.

---

## Docker, make, Windows

| | |
|---|---|
| `./mvkit <cmd>` | native if ffmpeg + whisper-cli are on PATH, else Docker |
| `./mvkit --docker <cmd>` | force Docker |
| `mvkit.cmd <cmd>` | Windows, always Docker |
| `make <target> SONG=x` | `drehbuch transcribe scenes refs split draft build all` |
| `./mvkit probe` | ask a running ComfyUI what it has and what to title what |
| `./mvkit workflows <song> [--from wf.json]` | write the graphs, or wrap your own |
| `./mvkit verify <song>` | measure the timing instead of trusting it |
| `make check` | syntax-check every script |
| `docker compose build` | build the image (whisper.cpp + ffmpeg + python) |
| `./mvkit llm-up` | start the local drafting model |

The container carries whisper.cpp, ffmpeg and python, so **Docker alone is
enough** - no local Python or Homebrew needed. The repo is bind-mounted, so edits
take effect without a rebuild. The whisper model cache is reused from
`~/.cache/whisper` when you already have one, otherwise `./.cache/whisper`.

One caveat: transcription in the container is CPU-only and slow - roughly 15x
slower than real time with the default `ggml-large-v3-turbo` model. Every other
step is instant. If that matters, either install whisper.cpp natively (a 2:47
song takes ~37 s) or trade accuracy for speed:

```bash
WHISPER_MODEL_NAME=ggml-base.bin ./mvkit --docker transcribe mysong
```

---

## Known limitations

- The ASR text is wrong on sung material and is not meant to be used as text -
  only its timings are. Real lyrics come from `_source/lyrics.txt` or from the
  screenplay's quoted lines.
- `transcribe` re-fills coverage gaps automatically, but check `coverage_pct`
  and `uncovered` in `transcript.json`.
- Claude cannot read pre-existing files in `~/Downloads` on macOS (TCC). Copy
  the file elsewhere or grant Full Disk Access.
- Scanned PDFs have no text layer, so `mvkit drehbuch` comes back empty. Write
  `drehbuch.txt` by hand.
- Whisper fills trailing silence with one hallucinated line repeated to the end
  of the file. `transcribe` finds the last real audio from the silence log and
  drops what sits after it, but check `segment_count` if a song has a long tail.
- The ComfyUI nodes have not been run inside a live ComfyUI - there is none on
  the machine they were written on. Their parsing, grid and tag logic is tested
  standalone. Two VideoHelperSuite connections in the upscale graph are flagged
  in `__READ_ME.txt` as needing one look in the UI, because VHS has renamed both
  between versions.

## Grade artefacts stay out of the prompt

The `[style]` block explicitly forbids grain, video noise, VHS softness, scanlines,
chroma bleed, gate weave, dust, halation and lens effects. The prompt describes
the *craft* of the era instead - how the line was drawn, how the paint was laid,
animation on twos, mouth charts, rostrum camera - never the condition of an old
tape. The period damage goes on afterwards in DaVinci, where you can still take
it off. It is also what makes the upscale pass work: a clean plate upscales, a
grainy one amplifies its grain.

For a 90s broadcast grade, the artefacts that actually read are composite video
ones: chroma bleed and dot crawl, slight horizontal smear, interlace combing on
motion, head-switching noise along the bottom edge, occasional tape dropout, a
little vertical jitter, and clipped NTSC/PAL saturation.

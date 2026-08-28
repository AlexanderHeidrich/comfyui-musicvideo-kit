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
  style.txt             the look, from templates/styles/90s-cartoon-dirty.txt
  style_examples.txt    free notes: "like Ren & Stimpy but rougher"
  bible.txt             cast, world, rules  (a TODO skeleton)
  tail.txt              global audio block
  lyrics.txt            the real lyrics, optionally [mm:ss] prefixed
  content.json          {}
  refs/__README.txt     the reference naming schema
```

### 2. Drop in the screenplay and the references

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
```

Real output from the scenes step on this song:

```
drehbuch: 50 scenes, frame numbers read at 24 fps (H3 renders at 24 fps)
scenes           : 49
covers           : 0.000 -> 171.417 s  (song 167.314 s, +4.103)
durations        : 5.167 .. 12.250 s  (all on the 17k+5 grid: True)
longest tail     : +0.667 s of clip past its scene, trim in the edit
! 1 scene(s) end at or before 0.0s (Vorspann, no music yet) - dropped
! 39 scene(s) were shorter than H3's 5.17s minimum - padded, so they overlap
```

Read those warnings. They are the honest report of what H3 could not do.

### 4. Write the prose, rebuild

`draft` seeds `content.json` from the screenplay so the folder already renders.
Then improve it - by hand, with Claude (`.claude/skills/storyboard/`), or with a
local model:

```bash
./mvkit llm-up                       # ollama + gemma3:4b in Docker, ~3 GB, once
./mvkit draft federphibien --llm     # rewrites content.json into shot language
./mvkit build federphibien
```

Edit `_source/bible.txt`, `_source/style.txt`, `_source/tail.txt`,
`_source/content.json` - never the generated files - and re-run `build`.

### 5. Get it into ComfyUI

The `NN_title-vN.txt` files are **finished H3 prompts** - MiniMax's six sections,
no markup, nothing to strip. Paste one in exactly as it is.

One scene = one H3 render, so a whole song is 49 renders per camera variant.
Core ComfyUI has no node that reads a text file and no way to load audio from a
path, so batching needs either two node packs or the HTTP API:

```bash
./mvkit queue Federphibien workflow_api.json --variant v1 --dry-run
```

**[docs/comfyui-batch.md](docs/comfyui-batch.md)** has the whole thing: which
nodes, how to wire them, and why the stock ones are not enough. The deliverable
ships what both paths need - `__SCENES.tsv` (frames and pairing per scene) and
`__batch/` (line-aligned prompt/audio lists, grouped by frame count so `length`
is set once per group instead of once per scene).

### 6. Join the clips

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

## What a finished song folder holds

```
songs/federphibien/
  __READ_ME.txt        what this folder is
  __SCENES.tsv         scene, start, end, frames, duration, cut, audio, prompts, lyrics
  NN_title-v1.txt      a paste-ready six-section H3 prompt
  NN_title.mp3         the audio slice, shared by v1/v2/v3
  __batch/             line-aligned lists for batching, grouped by frame count
  ALL_scenes.txt       the same material in this kit's DSL, for mv_h3_nodes.py
  _source/             every input; nothing here is meant to be copied out
```

The `@BIBLE` / `@STYLE` / `@SCENE` / `@TAIL` markers are **this kit's DSL, not a
MiniMax convention** - they only appear in `ALL_scenes.txt`, which is what the
ComfyUI storyboard node reads. The per-scene files carry no markup at all.

## What is in a scene

`NN_..-v1/-v2/-v3.txt` are **coverage, not alternatives**: the same action from
three cameras - v1 wide master, v2 other angle, v3 close/detail. The ACTION text
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
  cameras/              camera sets to pick from - drop one over cameras.txt
    __GLOSSARY.txt      shot sizes, angles, moves, and H3's bracket commands
    static-coverage.txt  moving-coverage.txt  rostrum-2d.txt
    handheld-doc.txt     anime-drama.txt
  styles/               look blocks: 90s-cartoon-dirty.txt, _TEMPLATE.txt
  bible/  tail/         cast and audio skeletons
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

## Grade artefacts stay out of the prompt

`style.txt` explicitly forbids grain, video noise, VHS softness, scanlines,
chroma bleed, gate weave, dust, halation and lens effects. The prompt describes
the *craft* of the era - ink taper, flat fills with hard-edged shadow tones,
gouache backgrounds, animation on twos, mouth charts, rostrum camera. The period
damage goes on afterwards in DaVinci, where you can still take it off.

For a 90s broadcast grade, the artefacts that actually read are composite video
ones: chroma bleed and dot crawl, slight horizontal smear, interlace combing on
motion, head-switching noise along the bottom edge, occasional tape dropout, a
little vertical jitter, and clipped NTSC/PAL saturation.

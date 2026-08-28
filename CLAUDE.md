# MusicVideoKit — working notes for Claude

A pipeline that turns a song into per-scene storyboards for **MiniMax H3
reference-to-video (ref2va)** in ComfyUI. Read this before touching anything.

There is a committed skill at `.claude/skills/storyboard/SKILL.md` that runs the
whole intake and wiring. Use it when the user wants a song storyboarded; this
file is the reference behind it.

## One entry point

`./mvkit <command>` (bash) or `mvkit.cmd <command>` (Windows, via Docker) or
`make <target> SONG=<name>`. It picks the engine itself: native when ffmpeg and
whisper-cli are on PATH, Docker otherwise. Force with `--native` / `--docker`.

```
new <name> <audio> [style]   scaffold songs/<name>/_source with every input slot
drehbuch   <song>            _source/*.pdf     -> _source/drehbuch.txt
transcribe <song>            audio             -> transcript.json/.tsv/.txt
scenes     <song> [args]     drehbuch+transcript -> scenes.tsv (the timing spine)
refs       <song>            _source/refs/     -> refs.json + the live H3 tags
split      <song>            song              -> scene_NN.mp3
draft      <song> [--llm]    screenplay+lyrics -> content.json
build      <song>            all blocks        -> the flat NN_*.txt deliverable
all        <song>            every step above, in order
concat <dir> [out]           join rendered clips
llm-up / llm-down            local drafting model (ollama + gemma3:4b, Docker)
doctor                       what is installed, which engine will run
```

## Layout

```
mvkit  mvkit.cmd  Makefile  Dockerfile  docker-compose.yml
bin/            the steps. _lib.sh resolves ffmpeg/python/whisper per platform
templates/      everything tunable without code - see templates/__README.txt
songs/<name>/                DELIVERABLE — flat and paired, nothing else
  __READ_ME.txt              generated; what the user reads
  __SCENES.tsv               frames, timing and pairing per scene
  NN_title-v1.txt            scene NN, wide master - a finished six-section
  NN_title-v2.txt            H3 prompt, no markup, paste-ready
  NN_title-v3.txt            same action, close/detail
  NN_title.mp3               that exact window of the song, shared by v1-v3
  __batch/                   line-aligned prompt/audio lists, grouped by frames
  ALL_scenes.txt             every scene in the DSL, for the ComfyUI node
  _source/                   INPUTS — everything not meant to be copied
    song.mp3                 the track
    song.pdf                 the screenplay, any name (optional)
    drehbuch.txt             extracted or hand-written spine (optional)
    refs/                    reference images, named by schema (see its __README)
    lyrics.txt               the real lyrics, optionally [mm:ss] prefixed
    style.txt style_examples.txt bible.txt tail.txt
    content.json             one entry per scene
    transcript.* scenes.tsv refs.json     generated
```

Never hand-edit the generated files. Edit `_source/*` and re-run `mvkit build`.
`songs/*` is gitignored: the folder is the user's deliverable, not repo content.

## Hard constraints from MiniMax H3

Verified against `comfy_extras/nodes_minimax_h3.py`, not guessed.

- **Frame grid.** `length` is only valid where `frames % 17 == 5`, trained range
  124–362, and H3 **rounds up**. Asking for 5.20 s silently yields 5.875 s. So
  every scene duration must be picked *from* the grid — that is the whole job of
  `make_scenes.py`. Grid seconds: 5.167, 5.875, 6.583, 7.292, 8.000, 8.708,
  9.417, 10.125, 10.833, 11.542, 12.250, 12.958, 13.667, 14.375, 15.083.
- **Max ~15 s per generation.** One scene = one render. There is no loop node in
  ComfyUI core; iterate with a scene index set to `increment` plus batch count.
- **Reference tags renumber.** H3 skips unconnected slots and numbers the
  survivors 1..n per type. Leave picture slot 1 empty and `<Picture 2>` becomes
  `<Picture 1>`. Worse: a reference video's own soundtrack claims an `<Audio>`
  number *before* any standalone audio. Never hardcode tags — run `mvkit refs`
  and read them off `refs.json` / the reference-inventory node.
- **Limits.** 9 reference images, 3 videos (each may carry its own audio), 3
  standalone audio, max 12 media total. Audio alone is not a valid input; there
  must be at least one image or video.
- **Prompt shape.** The official six sections in order: `subject_definitions`,
  `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`,
  `non_diegetic_music`. Internal cuts are written `At 00:0X.XXX, cut to
  [Shot N]`; the first shot carries no timestamp. Dialogue stays verbatim in its
  original language. Concrete physical detail — never "cinematic", "epic".
- **English descriptions, verbatim lyrics.** Every title, summary and shot
  description is written in English however the screenplay was written; H3
  follows English shot language far more reliably. Lyrics and dialogue stay
  verbatim in their own language. `mvkit build` warns when a description still
  reads as German.
- **Camera moves** are bracket commands (`[Push in]`, `[Pan left]`,
  `[Static shot]`, …), at most three simultaneously, and `[Push in]` is not
  `[Zoom in]`. There is no negative_prompt. See `templates/cameras/__GLOSSARY.txt`.

## The screenplay spine

`_source/drehbuch.txt` drives the split when it exists; otherwise `scenes` falls
back to `--uniform 10`. Blocks headed by `Frame <a> bis <b>` (or `-`, `to`, or a
`<start>-<end> | title | desc` line, or `f<n>` / `mm:ss.sss` values). Quoted text
in a block becomes that scene's lyric, the rest becomes its action. FPS is read
from a `# fps: N` line or from prose like "24 FPS", and only converts frame
numbers — H3 still renders at 24.

**Two different timing models, on purpose:**

- *Screenplay mode* anchors every scene to its own start and rounds its length
  **up** to the grid, so each clip always covers its scene and carries a small
  tail into the next. Scenes below H3's 5.167 s minimum are padded (they overlap
  more), scenes above 15.083 s are split into parts. Overlap, not drift — the
  user trims in DaVinci.
- *Uniform / --at / --sections mode* lays scenes end to end, so there is no
  cumulative drift and the audio slice equals the clip length by construction.

`mvkit drehbuch` extracts the PDF with the stdlib only (`bin/pdf_text.py`,
FlateDecode + ToUnicode CMaps, headings detected by font size and turned into
separator rules). Scanned PDFs have no text layer and come back empty.

## Gotchas that will bite you

**macOS TCC.** This process often cannot read pre-existing files in
`~/Downloads` — a `cp` returns "No such file or directory" even though `ls`
works. Ask the user to copy the file elsewhere, or to grant Full Disk Access.
Do not waste turns re-probing.

**ffmpeg eats stdin.** Any `ffmpeg` inside a `while read` loop must be called
with `-nostdin` or it drains the loop's input and the loop silently mangles
itself. This bit `split_audio.sh` — it survived on macOS and corrupted the
scene list in the container.

**Whisper lies in three specific ways** on sung material, all seen on real runs:
1. It smears one guessed word across a long instrumental intro — a "segment"
   claiming 0–20.7 s was a single word stretched over the intro. Check the
   *word* timings to find the true vocal onset.
2. It hallucinates past the end of the file. A 167.3 s song produced words out
   to 196.9 s. Discard anything beyond `duration`.
3. It silently gives up mid-song. A first pass covered only 115 s of 143 s.
   `transcribe.sh` now detects coverage gaps and re-transcribes them; check the
   reported `coverage_pct` and `uncovered`.

The transcript's **words will be wrong** on sung German ("Nachkömmlinge von
Frosch und Henne" came back as "Nachkümmlinge von Rausch und Herde"). That is
fine and expected. You are not using it for text — the real lyrics come from
`_source/lyrics.txt` or from the screenplay's quoted lines. You are using the
transcript for **timings only**.

**No Python whisper on this machine.** Python is 3.14 with PEP 668; neither
ctranslate2 nor torch ship wheels for it. Use whisper.cpp (`brew install
whisper-cpp`) with a ggml model, or just use Docker. Do not try
`pip install faster-whisper`.

**Docker build on arm64.** ggml's NEON fp16 paths do not compile under gcc-12
with `-mcpu=native`; the Dockerfile pins `-DGGML_NATIVE=OFF
-DGGML_CPU_ARM_ARCH=armv8.2-a+fp16`. Do not "simplify" that away.

**Do not trust `cmd | tail` for exit codes** — you get tail's. And this shell is
zsh, so it is `$pipestatus[1]`, not `$PIPESTATUS[0]`.

**macOS bash is 3.2.** No associative arrays, no `${var^^}`, no `mapfile`.

## Style rule that is easy to break

Every style block ends with a **RENDER CLEAN** section forbidding grain, noise,
VHS softness, scanlines, chroma bleed, gate weave, dust, halation, vignetting
and lens effects. The user adds all period artefacts afterwards in DaVinci, and
baked-in artefacts cannot be removed. Describe the *craft* of the era — ink
taper, flat fills with hard-edged shadow tones, gouache backgrounds, animation
on twos, mouth charts, rostrum camera — never the *condition of an old tape*.
Keep that section when editing any style.

Show and brand names ("like Ren & Stimpy") belong in `_source/style_examples.txt`
or in `#` comments, which are stripped before the text reaches the model. They
do not reproduce reliably; concrete craft descriptions do.

## Variants convention

`NN_slug-v1/-v2/-v3.txt` are **coverage of one moment, not alternative scenes**:
v1 = wide master, v2 = alternative angle/medium, v3 = close/detail. The ACTION
block is byte-identical across all three; only the CAMERA block differs, so they
can be cut together inside one scene, and all three share the single
`NN_slug.mp3`. There is no separate base file — v1 is the master. If you
regenerate them, preserve that property; it is the point.

**v1 is the director's shot.** Whatever framing the screenplay states is what v1
does - `mvkit scenes` extracts it into the `framing` column of scenes.tsv, and
`mvkit build` warns when a scene has one that v1 ignores. v2 and v3 are coverage
chosen by film-theory practice (never repeat v1's size, cross the axis, give one
of them something the master cannot hold); `templates/cameras/__COVERAGE.txt` has
the table.

Cameras live per scene in `content.json` under `"cameras": {"v1": ..., "v2": ...,
"v3": ...}`. A scene without that key falls back to `templates/cameras.txt` (or a
song's own `_source/cameras.txt`), which is the generic wide/angle/detail set -
fine for a song with no screenplay, not fine for one that has one. Add a `[v4]`
block or a `v4` key and it is generated too.

Because the action is reused byte-for-byte, it must not name a framing —
"close-up" in the action contradicts the wide master. `mvkit build` lints for
that too. Story staging (a focus rack, one character looming out of frame) is
action, not framing, and stays.

Where a scene is long enough it also carries an internal cut (`inner_cut_rel` in
scenes.tsv) placing a **Shot 2 that is harvestable B-roll**, so a 10 s clip
yields both its lyric moment and a reusable atmosphere shot. The cut is snapped
to the nearest real ASR segment boundary so it never lands mid-word, or to the
join when two screenplay scenes were merged; `cut_on_boundary` says which.

## Render side (ComfyUI)

Needs `mv_h3_nodes.py` in `ComfyUI/custom_nodes/` — one stdlib-only file
providing three nodes, because core ComfyUI has no node that performs an HTTP
request and none that reads a text file from disk:

- `MVStoryboardScene` — parses the DSL, picks scene N, outputs timing and frames
- `MVReferenceInventory` — computes the live `<Picture n>`/`<Video n>`/`<Audio n>`
  tags from actual connections, mirroring H3's ordering
- `MVPromptBuilder` — optional LM Studio pass (OpenAI-compatible
  `/chat/completions`); with `use_llm = false` it emits a valid six-section
  prompt from a deterministic template

Everything else in the workflow is stock comfy-core - but note that core has no
text-file loader and `LoadAudio` only sees `ComfyUI/input`, so batching a folder
needs VideoHelperSuite + WAS Node Suite, or `bin/queue_comfy.py` over the HTTP
API. See `docs/comfyui-batch.md`; keep it in sync if the deliverable changes.

## Storyboard DSL

**This is the kit's own format, not a MiniMax convention.** It appears only in
`ALL_scenes.txt`, which `MVStoryboardScene` reads. The per-scene `NN_*.txt` files
are finished six-section H3 prompts with no directives and no comments, because
they are meant to be pasted straight in. Do not reintroduce markup there.

Directives sit alone at the start of a line; `#` is a comment.

```
@BIBLE   constant frame, prepended to every scene
@STYLE   constant look
@SCENE mm:ss.sss-mm:ss.sss | title
@TAIL    constant frame, appended to every scene
```

The `@SCENE` range is **absolute song time**. It sets the clip length *and* the
slice of the track used as audio reference, which is what keeps picture on beat.

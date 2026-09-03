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
build      <song> [--all-sheets]  all blocks   -> the set-*/ deliverable
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
songs/<name>/                DELIVERABLE
  __READ_ME.txt              generated; what the user reads, incl. the work list
  __SCENES.tsv               frames, timing, pairing and set folder per scene
  set-NN_<sheets>/           one folder per set of reference sheets, and the
                             thing you actually render - see "Reference sets"
    NN_title-v1.txt          scene NN, wide master - a finished six-section
    NN_title-v2.txt          H3 prompt, no markup, paste-ready
    NN_title-v3.txt          same action, close/detail
    NN_title.mp3             that exact window of the song, shared by v1-v3
    <name>-set-NN_*.json     the graph for that set
  <name>-4x.json             the upscale pass
  _source/                   INPUTS — everything not meant to be copied
    song.mp3                 the track
    song.pdf                 the screenplay, any name (optional)
    drehbuch.txt             extracted or hand-written spine (optional)
    refs/                    reference images, named by schema (see its __README)
    lyrics.txt               the real lyrics, optionally [mm:ss] prefixed
    brief.txt                the ONLY source of the prompts
    style_examples.txt tail.txt
    content.json             one entry per scene
    transcript.* scenes.tsv refs.json     generated
```

Never hand-edit the generated files. Edit `_source/*` and re-run `mvkit build`.
Song folders ARE versioned - refs, style and screenplay are work, not build
output. Only rendered video is ignored (`.gitignore`).

A build rewrites the set folders from scratch. The audio slices are the one thing
in them that cannot be regenerated from the inputs, so `reclaim_slices()` moves
them back to the song folder first and the fresh sets take them again.

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
  `non_diegetic_music`. `summary` opens with a bracketed task type
  (`[reference generation + audio reuse]`), `retention_analysis` is one
  generated line per reference label carrying H3's fixed markers
  (`fully_preserved` / `partially_preserved` / `attribute_transfer` /
  `weak_reference`, and `fully_copy` / `partially_copy` / `reference` for audio),
  and the **style belongs before `[Shot 1]` in `detailed_description`** - not in
  `retention_analysis`, which is a reference ledger, not a look brief. Internal cuts are written `[Shot N] At
  00:0X.XXX, the shot cuts to:` - the label first, then the time, per MiniMax's
  own guide. `[Shot 1]` opens the first shot and carries no timestamp. Dialogue stays verbatim in its
  original language. Concrete physical detail — never "cinematic", "epic".
- **Every prompt stays under 7,000 characters.** That is the length every
  published H3 guide documents. It used to be ignored: a whole long-form bible
  went into
  `subject_definitions` and the whole style into `detailed_description`, and a
  built scene ran ~28,000 characters with the shot description at ~19,000. If
  the ComfyUI path truncates the way the hosted API does, H3 read a cast list
  and nothing else — which is exactly what a reference turning up in every scene
  looks like. Whether it truncates is still unproven, so the prompts are simply
  built to fit: `_source/brief.txt` holds a short block per reference, a scene
  carries only the subjects it contains, and `mvkit build` names any scene that
  overruns - the `fit-prompts` skill is what then shortens it, because choosing
  what to cut is judgement and a truncating script would cut the shot off the
  end, which is the failure the limit exists to avoid. There is no long form any
  more: `brief.txt` is the only source, and `bible.txt` / `style.txt` /
  `ALL_scenes.txt` are gone from the pipeline entirely.
  Sources: rundiffusion.com/minimax-h3-prompt-guide, fal.ai/learn/devs/minimax-h3-prompting-guide.
- **A reference not in the shot must not be connected.** Words do not undo a
  connected picture: with all sheets wired in, a scene that said "do not use
  `<Picture 5>`" still got it as its first frame. So presence decides the wiring,
  not just the text - see "Reference sets" below. Presence is derived from the
  words in the action;
  `_source/refs/__ALIASES.txt` maps a reference slug to the English words that
  mean it is on screen (`-phrase` blanks a phrase first, so "hen" does not match
  inside "hen house"), and a scene may override the guess with a `"cast"` list in
  content.json. `mvkit build` prints the per-scene cast and warns when a scene
  names no character at all. `mvkit build --all-sheets` is the old behaviour -
  every sheet on every scene, global tags, absence stated in a `weak_reference`
  line and believed - kept only so a render made that way can be reproduced.
- **English descriptions, verbatim lyrics.** Every title, summary and shot
  description is written in English however the screenplay was written; H3
  follows English shot language far more reliably. Lyrics and dialogue stay
  verbatim in their own language. `mvkit build` warns when a description still
  reads as German.
- **Camera moves are natural English, not bracket commands.** `[Push in]` and
  friends are Hailuo 02's grammar; H3 dropped it and wants *motion type +
  amplitude + speed* written as a sentence inside the shot - "The camera pushes
  in with small amplitude at slow speed." Brackets stay this kit's authoring
  shorthand in `content.json` and `cameras.txt`, and `camera_sentence()` in
  `build_storyboards.py` translates them on the way out; anything it does not
  recognise is dropped with a warning. `[Push in]` is still not `[Zoom in]` - a
  push travels and changes parallax, a zoom only changes focal length, and asking
  for a push when you meant an aerial zoom is how a plan view turns into a
  descent through the trees. One dominant move per clip. There is no
  negative_prompt. See `templates/cameras/__GLOSSARY.txt`.
- **Scale is not in the references.** Every reference is a portrait filling its
  own frame, so H3 has nothing to size characters by and will draw them all the
  same size - a frog as big as a man. Every `[subject]` block in `brief.txt`
  carries real measurements and the relation to the other characters, and every
  shot that holds two of them restates which is bigger.

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

## Continuity

`First Frame <> Last Frame` in a screenplay marks one unbroken camera setup.
`fuse_holds()` in make_scenes joins a run of held, touching scenes into a single
generation when the total still fits the grid, with an internal cut at each join;
otherwise the later parts get `chain` in the `continuity` column and must be
rendered in order off the previous clip's last frame. `hold` alone only means the
shot begins and ends on the same framing - it does not imply continuation, and
the phrase list that does imply it is deliberately narrow ("Kamera bleibt
statisch" is a locked-off camera, not a continuation).

A scene can carry more than two shots: `content.json` takes `shot1`, `shot2`,
`shot3`, ... and `scenes.tsv` an `inner_cuts` list, one timestamp per join.

`mvkit shotlist` writes the reference plan from `brief.txt`: which images are
worth making, ranked by how many scenes each character is in, with generation
prompts built from the `[style]` block so a sheet cannot fight the look. A
`[subject]` written `{S} is ... shown in {P}` is a character and gets a sheet;
one written `{P} is ...` is a location or board and is only listed. It flags
entries that derive a character from a `<Picture n>` that does not exist yet.

## Verifying the timing

`mvkit verify <song>` measures rather than trusts: the grid rule, `duration ==
frames/24`, `end == start + duration`, each slice's decoded length, and where each
slice actually sits in the song (coarse PCM search, +/-60 ms). Run it after any
change to make_scenes or split_audio. On Federphibien it reports worst +0.7 ms on
length and +0.0 ms on position across 47 slices.

Slices are padded with silence to their exact declared length. A scene anchored
near the end of the song runs past it - Federphibien's last scene starts at
166.25 s of a 167.31 s song and is padded to H3's 5.167 s minimum - and handing
H3 an audio reference shorter than the clip it drives is worse than handing it
silence. split_audio reports how much it padded.

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

## Reference sets

The wiring is per set of sheets, not per song and not per scene. A saved ComfyUI
graph cannot change how many links it has, `ExecutionBlocker` blocks the consumer
rather than dropping an input, and there is no way to hand H3 "nothing" on an
`IMAGE` slot - so the number of connected reference images is fixed for a whole
graph. Scenes that need the same sheets therefore share a graph:

- `scene_slots()` in build_storyboards works out which sheets a scene contains
  (`in_shot()`: a character when the action names it, a place or a board unless
  its aliases miss) and numbers them **locally**, `<Picture 1>` first. H3
  renumbers whatever it is handed, so those are the numbers it will use.
- `write_refsets()` groups the scenes by that tuple and writes one folder per
  group, biggest first: `set-NN_<sheet numbers>/` with that group's prompts, its
  audio slices and its own `__SCENES.tsv`. Each folder is a song folder in its
  own right - `HurricaneSongFolder` points straight at it - and the song's
  `__READ_ME.txt` carries the work list.
- `mvkit workflows <song> --from <graph>` writes one graph per set into its
  folder, keeping only the image loaders that set needs and wiring them into
  `ref_image_0..k-1` in the set's own order. Sheet *n* is whatever fed H3's *n*th
  image slot in the graph you saved, so **the loaders must be connected in the
  order `__READ_ME.txt` lists the sheets** before you save.
- The source graph is kept as `_source/workflow.json` and every build re-grafts
  from it, because a build rewrites the set folders from scratch.

Federphibien: 49 scenes, 7 sheets, 18 sets, widest 5. Do not "simplify" this back
into one graph with all sheets connected - that is the bug it replaces.

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

**All three are built from `_source/brief.txt`**, which is required: `[style]`,
`[sound]`, `[music]` and one `[subject <ref slug>]` per reference, where `{S}`
becomes the scene's live `<Subject n>` and `{P}` its `<Picture n>`. A prompt
carries only the subjects the scene contains, with the guide's `<Subject n> is
... shown in <Picture n>` binding, and the sheets it does not contain are simply
not in the prompt and not in the graph. That is what holds a scene near 6 KB
instead of the 30 KB the old full build produced. `mvkit build` prints the
longest prompt per variant and names every scene over 7,000 characters; the
levers are that scene's action in content.json and the `[subject]` / `[style]`
blocks, which are in every prompt.

Cameras live per scene in `content.json` under `"cameras": {"v1": ..., "v2": ...,
"v3": ...}`. A scene without that key falls back to `templates/cameras.txt` (or a
song's own `_source/cameras.txt`), which is the generic wide/angle/detail set -
fine for a song with no screenplay, not fine for one that has one. Add a `[v5]`
block or a `v5` key and it is generated too.

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

Ships `comfyui/custom_nodes/watching_hurricanes.py` — copy or symlink it into
your own `ComfyUI/custom_nodes/`. One stdlib-only file with **one** node, because
core ComfyUI has no node that reads a text file from disk:

- `HurricaneSongFolder` — point it at one `songs/<name>/set-*/` and it batches
  that set, reading its `__SCENES.tsv` for the pairing. Outputs the finished prompt, the
  slice's path, the frame count, the scene count and a save prefix. Paths are
  STRINGs on purpose: building an IMAGE or AUDIO needs torch, and the file has no
  dependencies. Set `scene_index` to `increment`, batch count to `scene_count`,
  run once. That is the whole render workflow — there is no HTTP path and nothing
  to queue from the host.

A second, independent file `comfyui/custom_nodes/watching_hurricanes_upscale.py`
holds the pass afterwards — deliberately separate, sharing no code and with no H3
in it:

- `HurricaneClipFolder` — walks a folder of rendered clips in name order, so
  takes you deleted are simply not in the run. Refuses an index past the end
  rather than silently re-rendering the last clip all night.
  `__workflow_upscale.json` wires it to one 4x line-art model
  (`RealESRGAN_x4plus_anime_6B`) and writes whatever comes out — **no scaling
  node after the model**, so the output is 4x the render and hitting 4K exactly
  is the edit's job. A diffusion upscaler is the wrong tool here: it invents
  texture in flat fills, and invents it differently per frame.

`mvkit build` writes `<song>-4x.json` into every song folder - the pass after
rendering, complete and standalone. It does NOT generate a render graph:
`MiniMaxH3ReferenceToVideo` returns `positive`/`LATENT`, so a working graph needs
a UNET loader, CLIP and VAE loaders, a sampler, a VAEDecode *and* a
VAEDecodeAudio, and a CreateVideo - ComfyUI ships that chain under Browse
Templates and guessing at it is worthless.

`mvkit workflows <song> --from <your workflow.json>` grafts a graph that already
renders, once per reference set. It takes the **saved** UI format only and edits
it in place (`wrap_ui`) so the layout and groups survive; an API export is
refused, because it has neither and is not the file you open again. `mvkit layout`
builds a layout from scratch for a graph that has already lost one. The graft
keeps every node and setting and rewires only `prompt`, `length`,
`ref_audios.ref_audio_0`, the Save node's `filename_prefix` and the
`ref_images.ref_image_*` slots - note the namespaced input names, and that the
ref slots are DYNAMIC, so it can only use as many as the user connected before
saving. Loaders a set does not need are removed, the rest are retitled with the
number that set's prompts use. `--all-sheets` grafts the pre-set wiring instead,
which only matches a `mvkit build --all-sheets` folder. No absolute path is ever
written: ComfyUI usually runs on another machine, so `song_path` is left empty
and `find_abs_paths` makes the build fail rather than emit one. Earlier generated
graphs, the whole-song `<song>.json` and the old `-api.json` copies are deleted on
sight.

The weights, for reference: UNET `minimax_h3_ref2va_pruned_int8_convrot`, CLIP
`qwen3vl_*_minimax_h3_*`, `vae` = `minimax_h3_video_vae_fp16`, `audio_vae` =
`minimax_h3_audio_vae_fp32`. There is one right answer per slot. The sibling
`minimax_h3_fl2va` is first-and-last-frame to video and is the model for scenes
marked `chain` — ref2va cannot continue off a previous clip's last frame at all.

`mvkit probe` reads a running server's `/object_info` and reports which nodes are
actually installed - useful after a node-pack update, not part of the job.
Splitting stays in the kit: ComfyUI never sees the pdf or the full mp3, only a
built folder.

Everything else in the workflow is stock comfy-core - but note that core has no
text-file loader and `LoadAudio` only sees `ComfyUI/input`, which is why
`HurricaneSongFolder` exists. Without it, batching a folder needs VideoHelperSuite
+ WAS Node Suite. See `docs/comfyui-batch.md`; keep it in sync if the deliverable
changes.

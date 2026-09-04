# MusicVideoKit — working notes for Claude

A harness that turns a song and its screenplay into per-scene storyboards for
**MiniMax H3 reference-to-video** in ComfyUI. Read this before touching anything.

**An agent writes the prompts; the scripts only file them.** There is no
template merger. `.claude/skills/storyboard/SKILL.md` runs the whole job.

## Before changing anything about quality

Verify against the web first — MiniMax's docs, ComfyUI's docs, or a published
prompt guide — and say which source. Reference handling, prompt structure and
anything touching adherence are not to be changed on intuition. The notes in
this repo have drifted from reality more than once; so has `refs/__PROMPTS.txt`,
which once recommended the exact wiring that caused a rendering bug documented
three sections below.

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

## Layout

```
songs/<name>/                DELIVERABLE
  __READ_ME.txt              generated; the work list and the loader order
  __SCENES.tsv               scene -> set, title, location, sheets
  set-NN_<sheets>/           one folder per set of reference sheets
    NN_title-v1.txt          a finished six-section H3 prompt, paste-ready
    NN_title-v2.txt          same action, different camera
    NN_title-v3.txt          same action, close/detail
    <name>-set-NN_*.json     the graph for that set
    __SCENES.tsv             what HurricaneSongFolder reads
  <name>-4x.json             the upscale pass
  refs/                      reference sheets, named by schema — the one input
                             you wire into ComfyUI by hand
  _source/                   INPUTS
    song.mp3                 the track. The pipeline never reads it; it goes
                             under the picture in DaVinci
    song.pdf  drehbuch.txt   the screenplay, and its extracted spine
    brief.txt                the [style] / [sound] / [music] / [subject] /
                             [location] blocks you write prompts out of
    scenes.json              THE authored file: frozen full-text prompts
    style_examples.txt       free notes on the look, never sent to the model
    synopsis.txt             plain-language summary for a human
    workflow.json            the graph every set graph is grafted from
```

Never hand-edit the generated files. Edit `_source/scenes.json` and re-run
`mvkit pack`. A pack rewrites the set folders from scratch.

## Hard constraints from MiniMax H3

- **Frame grid.** `length` is only valid where `frames % 17 == 5`, trained range
  124–362, and H3 rounds up. This kit uses **243 frames = 10.125 s for every
  scene**; the node's length is set once and never touched.
- **Max ~15 s per generation** (362 frames). There is no 20 s. One scene = one
  render; iterate with `scene_index` on `increment` plus batch count.
- **Reference tags renumber.** H3 numbers `<Picture n>` over the slots actually
  connected, so a gap shifts every tag after it. Wire the loaders in the order
  `__READ_ME.txt` lists them, starting at `ref_image_0`, leaving no gap.
- **Limits.** 9 reference images, 3 videos, 3 standalone audio, 12 media total.
  Audio alone is not valid input.
- **Prompt shape.** Six sections in order: `subject_definitions`, `summary`,
  `retention_analysis`, `detailed_description`, `overall_soundscape`,
  `non_diegetic_music`. `summary` opens with a bracketed task type.
  `retention_analysis` is a reference ledger carrying H3's fixed markers
  (`fully_preserved` / `partially_preserved` / `attribute_transfer` /
  `weak_reference`) — not a look brief. The style belongs in
  `detailed_description` before `[Shot 1]`. Internal cuts are
  `[Shot N] At 00:0X.XXX, the shot cuts to:`; `[Shot 1]` carries no timestamp.
- **Every prompt stays under 7,000 characters.** `mvkit pack` fails otherwise,
  rather than truncating — a truncating script would cut the shot off the end,
  which is the failure the limit exists to avoid.
- **Camera moves are natural English, not bracket commands.** `[Push in]` is
  Hailuo 02 grammar; H3 wants motion type + amplitude + speed as a sentence
  inside the shot. One dominant move per clip. There is no negative_prompt.
- **Scale is not in the references.** Every sheet is its own frame, so H3 has
  nothing to size characters by. Every `[subject]` carries real measurements, and
  every shot holding two characters restates which is bigger.

## The four mistakes this kit was rebuilt to stop making

**1. Reference audio is a timbre anchor, not playback.** H3 does not play a
supplied clip back — it re-sings the prompt's own words in that clip's voice, at
a timing it invents, and the guides say the reference should carry *different*
words than the prompt. Feeding it a slice of the song under a lyric printed in
the same prompt produced clips singing the wrong words. **There is now no audio
reference anywhere**, no slices, no `lyrics.txt`, no transcript, and
`non_diegetic_music` asks for no music, no song and no voice. The song goes under
the picture in the edit. Nothing sings, so nothing is out of sync.

**2. A reference not in the shot must not be connected.** Words do not undo a
connected picture: with all sheets wired, a scene saying "do not use
`<Picture 5>`" still got it as its first frame. Presence is **declared** per
scene in `scenes.json`, never guessed from keywords, and `pack` groups scenes by
their sheet tuple so each graph connects exactly what its scenes contain.

**3. A prompt with no stated location invents one, and the style block decides
which.** `[style]` once carried "pale green-white water", so a proposal written
for the hen house happened in a pond. `[style]` now holds the look and nothing
else; every place-bound palette word lives in that place's `[location]` block;
and a location sentence naming the set and its `<Picture n>` is mandatory before
`[Shot 1]`.

**4. Neither the summary nor the action may name a framing.** Both are byte
identical across v1/v2/v3 — only the camera sentence differs — so "close-up" in
either contradicts two of the three. It also breaks the other way: an action
saying "the hen's head fills the space in front of him" describes what only a
side view shows, and defeats a camera asking for the frog's back.

Related: a character sheet must be a **turnaround** — front, side, back, top on
one image. A single front portrait is why "from behind" never worked; H3 had
never seen the frog's back. `refs/__PROMPTS.txt` holds the generation prompts and
the Midjourney v8 parameters (`--raw`, not `--style raw`; `--cref` and `--q` do
not exist in v8; `--oref` silently downgrades the render to v7).

## Variants convention

`NN_slug-v1/-v2/-v3.txt` are **coverage of one moment, not alternative scenes**:
v1 wide master, v2 alternative angle, v3 close/detail. `summary` and the action
are byte-identical across all three; only the CAMERA sentence differs, so they
cut together inside one scene. If you regenerate them, preserve that.

A beat shorter than 5 s is not stretched — it gets a **second setup of the same
moment** as an internal cut at 00:05.000 (a third at 00:07.000 under 2 s). The
second setup is the same moment from another axis, never the next action.

## The screenplay spine

`_source/drehbuch.txt` is the whole timing model: one scene per `Frame <a> bis
<b>` block, one to one, each 243 frames. A block naming several distinct actions
("Mehrere Cuts", two things happening) becomes two scenes. Quoted text in a block
is a lyric and does **not** go into the prompt.

`mvkit drehbuch` extracts the pdf with the stdlib only (`bin/pdf_text.py`).
Scanned pdfs have no text layer and come back empty.

## Gotchas that will bite you

**macOS TCC.** This process often cannot read pre-existing files in `~/Downloads`
even though `ls` works. Ask the user to copy the file elsewhere. Do not re-probe.

**ffprobe reports container length, not music.** Federphibien's mp3 is 207.2 s
but the music ends at ~167 s; the rest is digital silence at −91 dB. Measure with
`volumedetect` before believing a duration.

**Do not trust `cmd | tail` for exit codes** — you get tail's. This shell is zsh,
so it is `$pipestatus[1]`, not `$PIPESTATUS[0]`.

**macOS bash is 3.2.** No associative arrays, no `${var^^}`, no `mapfile`.

## Render side (ComfyUI)

`comfyui/custom_nodes/watching_hurricanes.py` — one stdlib-only node.
`HurricaneSongFolder` points at one `songs/<name>/set-*/` folder, reads its
`__SCENES.tsv` and outputs `prompt`, `frames`, `scene_count` and `save_prefix`.
There is no audio output. Set `scene_index` to `increment`, batch count to
`scene_count`, run once.

`comfyui/custom_nodes/watching_hurricanes_upscale.py` holds the pass afterwards,
deliberately separate: `HurricaneClipFolder` walks rendered clips in name order.
`<song>-4x.json` wires one 4x line-art model (`RealESRGAN_x4plus_anime_6B`) with
**no scaling node after it** — a diffusion upscaler invents texture in flat fills,
differently per frame.

**`LoadImage` only reads `ComfyUI/input/`.** The grafted graphs name the sheets
by bare filename, deliberately, so they survive being opened on whatever machine
ComfyUI runs on — which means the refs must be copied into `ComfyUI/input/` by
hand or every loader comes up empty. `song_path` is left empty for the same
reason and is filled in per set folder.

**`LoadImage` only reads `ComfyUI/input/`.** The grafted graphs name the sheets
by bare filename, deliberately, so they survive being opened on whatever machine
ComfyUI runs on — which means the refs must be copied into `ComfyUI/input/` by
hand or every loader comes up empty. `song_path` is left empty for the same
reason and is filled in per set folder.

`mvkit workflows <song> --from <saved.json>` grafts a graph that already renders,
once per set. It takes the **saved** UI format only and edits it in place so the
layout and groups survive. It rewires `prompt`, `length`, the Save node's
`filename_prefix` and the `ref_images.ref_image_*` slots, removes the loaders a
set does not need and retitles the rest. No absolute path is ever written:
ComfyUI usually runs elsewhere, so `song_path` is left empty and `find_abs_paths`
fails the build rather than emit one.

Weights: UNET `minimax_h3_ref2va_pruned_int8_convrot`, CLIP
`qwen3vl_*_minimax_h3_*`, `vae` = `minimax_h3_video_vae_fp16`, `audio_vae` =
`minimax_h3_audio_vae_fp32`. Set `ref_image_size` to `max`, not `match`: with a
four-view turnaround, `match` scales each view down until H3 starts guessing.

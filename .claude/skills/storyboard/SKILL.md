---
name: storyboard
description: Turn a song into per-scene MiniMax H3 storyboards in this repo. Use when the user wants to build a music video, add or rebuild a song under songs/, convert a Drehbuch/screenplay into scenes, write the prompts, or fix an existing storyboard. Handles the intake of mp3, screenplay, references and style notes.
---

# Storyboard a song

**You write the prompts. The scripts only file them.** There is no template
merger any more: `_source/scenes.json` holds the finished six-section text for
every scene and variant, frozen, and `mvkit pack` copies it into the set folders
and checks it. If you find yourself wanting a script to assemble a prompt out of
`brief.txt` at build time, that is the thing this kit was rebuilt to remove.

Read `CLAUDE.md` first - it carries the H3 constraints and the traps.

## Before you change anything about quality

Verify against the web first: MiniMax's docs, ComfyUI's docs, or a published
prompt guide. Do not change reference handling, prompt structure or anything
touching adherence on intuition, and say which source you used. The repo's own
notes have drifted from reality more than once.

## 1. Intake

Ask for it all in one message, in the user's language, and do not block on the
optional parts.

1. **The song.** An mp3 in `_source/`. It is never read by the pipeline - it is
   what the user lays under the picture in DaVinci.
2. **The screenplay.** A pdf or text file that says, per frame range, what
   happens. This is the whole spine. `./mvkit drehbuch <song>` extracts a pdf
   with the stdlib; scanned pdfs come back empty.
3. **The look.** What it should look like, and what it reminds them of. Their
   words go verbatim into `_source/style_examples.txt`; you condense them into
   the `[style]` block of `_source/brief.txt`.
4. **References.** Character sheets and location paintings in `<song>/refs/`,
   named per `refs/__README.txt`. Characters want a **turnaround** - front,
   side, back, top on one image - or H3 has never seen the character's back and
   will answer "from behind" with whatever view it has. `refs/__PROMPTS.txt`
   holds the generation prompts.

Lyrics are not an input any more. Nothing sings.

## 2. Split the screenplay into scenes

One scene per screenplay frame range, one to one. Every scene is **243 frames
(10.125 s)** - the node's length is set once and never touched.

- A beat under 5 s does not get stretched. It gets a **second setup of the same
  moment** inside the clip, as `[Shot 2] At 00:05.000, the shot cuts to:`. Under
  2 s, give it a third at 00:07.000. The second setup is the same moment from
  another axis, never the next action, or the clip runs away from the story.
- A beat over 10 s: if the screenplay names several actions ("Mehrere Cuts",
  two distinct things happening), split it into two scenes. If it describes one
  continuous thing, keep it whole and let the action compress.
- The point is coverage. The user cuts it himself and wants choice.

## 3. Write `_source/scenes.json`

One entry per scene:

```json
{ "scene": 30, "beat": [2185, 2240], "frames": 243,
  "title": "the ring in the leaf box",
  "location": "henhouse interior",
  "sheets": ["der frosch", "board", "henhouse interior"],
  "prompts": { "v1": "<full six-section text>", "v2": "...", "v3": "..." } }
```

`sheets` is **declared, not guessed**. A connected reference turns up on screen
whether the prompt asks for it or not, so this list decides the wiring. Name only
what is in the shot.

The prompt rules, all of them load-bearing:

- The six sections in order: `subject_definitions`, `summary`,
  `retention_analysis`, `detailed_description`, `overall_soundscape`,
  `non_diegetic_music`. `summary` opens with `[reference generation]` - which is
  the right task type precisely because no image here is a concrete frame.
- **Every sheet is a `<Subject n>`, locations included**, citing its image
  inside the definition: `<Subject 3> is the pond ... in <Picture 3>`. A
  standalone `<Picture n>` entry means "this image IS a frame" in H3's grammar,
  and writing the locations that way is what made it paste the pond in as frame
  one. `retention_analysis` is keyed the same way, one line per subject with the
  shots it appears in: `<Subject 1> (appears in [Shot 1], [Shot 2]):
  partially_preserved - ...`.
- **A location sentence is mandatory**, in `detailed_description`, after the
  style block and before `[Shot 1]`, naming the set's `<Subject n>`. A scene
  with no stated place gets invented one, and the style block's palette decides
  which.
- **The reference sheets are the style authority**, not `[style]` and not the
  Drehbuch's header. Look at them before writing about the look; if a word and a
  sheet disagree, correct the word. For Federphibien the sheets are pen and
  watercolour, calm and melancholy - not the "90er Jahre Cartoon, eher rau" the
  Drehbuch header also offers.
- **`[style]` holds the look and nothing else.** Every palette word tied to a
  place lives in that place's `[location]` block. This is why proposals written
  for the hen house kept happening in a pond.
- **Neither `summary` nor the action may name a framing.** Both are byte
  identical across v1/v2/v3; only the camera sentence differs. "Close-up" in
  either contradicts two of the three variants.
- Camera as motion type + amplitude + speed in plain English inside the shot -
  "The camera pushes in with small amplitude at slow speed." Never `[Push in]`.
  The motion type comes from H3's closed list - Zoom In/Out, Push In/Pull Out,
  Pan, Truck, Tilt, Pedestal, Arc Shot, Tracking Shot, Static Shot, Shake, POV,
  Roll - and the only amplitude and speed values are small/large and slow/fast.
  Medium amplitude and normal speed are the omitted defaults; do not write them.
  One dominant move per clip.
- No `<Audio>` reference anywhere, no lyrics, no singing. `non_diegetic_music`
  asks for no music, no song, no voice. Reference audio is a timbre anchor, not
  playback - handing H3 a slice carrying the prompt's own words is what produced
  clips singing the wrong lyrics.
- English throughout. Under 7,000 characters (the API limit); `mvkit pack` fails
  otherwise.
- Reference sheets must not look like frames: characters as turnarounds,
  locations as element boards on bare paper, never a finished 16:9 background
  painting. The spec and the grammar both treat a complete image as a frame.
- Every scene that holds two characters restates which is bigger. The sheets
  carry no scale.

Writing 51 scenes by hand means retyping the same blocks 51 times. Use a one-off
helper in the scratchpad to expand them, but **the output must be frozen full
text in scenes.json** - hand-editable, diffable, and never reassembled at build
time.

## 4. Pack and wire

```bash
./mvkit pack <song>
./mvkit workflows <song> --from <song>/_source/workflow.json
```

`pack` groups scenes by their sheet tuple into `set-NN_*/` folders, numbers the
sheets the way H3 will, writes each set's `__SCENES.tsv`, the song's
`__READ_ME.txt` and `__TIMELINE.tsv`, and fails on a prompt over 7,000
characters. `workflows` grafts one graph per set,
keeping only the loaders that set needs. Check its report: loader count per set
must equal the sheet count.

In ComfyUI, point `HurricaneSongFolder` at one set folder, `scene_index` to
increment, batch count to `scene_count`, run once.

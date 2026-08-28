---
name: storyboard
description: Turn a song into per-scene MiniMax H3 storyboards in this repo. Use when the user wants to build a music video, add or rebuild a song under songs/, convert a Drehbuch/screenplay into scenes, write style/bible/content blocks, or fix an existing storyboard. Handles the intake of mp3, screenplay, references, lyrics and style notes.
---

# Storyboard a song

You are wiring inputs into `songs/<name>/_source/` and then running the pipeline.
The scripts do the timing; you do the writing. Never hand-edit generated files.

Read `CLAUDE.md` in the repo root first - it carries the H3 frame-grid rules and
the traps. Read `templates/__README.txt` for what is configurable.

## 1. Intake - ask before doing anything

Ask for all of it in one message, mark what is optional, and do not block on the
optional parts. Use the user's language.

1. **The song.** "Where is the mp3?" On macOS you cannot read pre-existing files
   in `~/Downloads` - ask them to `cp` it somewhere else, or try the copy first
   and only ask if it fails.
2. **The style.** "Describe the look, and name whatever it reminds you of -
   shows, films, illustrators, an era." Their examples go verbatim into
   `_source/style_examples.txt`; you distill them into `_source/style.txt`.
   Offer the ready-made ones: `ls templates/styles/`.
3. **The screenplay.** "Do you have a Drehbuch? A pdf or text file that says,
   per frame range or per second range, what happens?" This is the single
   biggest quality lever - with it the scene split follows the story instead of
   a metronome. If they have none, you will use `--uniform`.
4. **References.** "Any reference images for the characters, the look, the
   locations?" They go in `_source/refs/` under the naming schema in
   `_source/refs/__README.txt`. At least one image or video is required - H3
   rejects audio-only input.
5. **The lyrics.** "Paste the real lyrics." The ASR transcript is wrong on sung
   material and is only used for timing. Optionally `[mm:ss]`-prefixed, which
   places each line on its scene automatically.

## 2. Scaffold and run the mechanical part

```bash
./mvkit new <name> <audio> [style-template]   # style-template from templates/styles/
# put the screenplay pdf in songs/<name>/_source/ and the refs in _source/refs/
./mvkit all <name>
```

`all` does: pdf -> `drehbuch.txt`, transcribe, scenes, refs, split, draft, build.
It always produces something renderable, so run it early and iterate.

Check its output before writing prose:
- `coverage_pct` and `uncovered` in `transcript.json`
- the warnings from the scenes step - padded scenes, split scenes, scenes
  dropped before 0 s, and how far the last scene runs past the song
- the tag table from the refs step. Never hardcode `<Picture 1>`; use what it
  prints.

## 3. Write the blocks

Edit only these, then re-run `./mvkit build <name>`:

- `_source/bible.txt` - cast, world, rules. Constant in every scene. Start from
  `templates/bible/_TEMPLATE.txt`. Name the reference tag that carries each
  character, and state what NOT to take from the reference (its rendering, any
  lettering or border in the image).
- `_source/style.txt` - the look. Start from a file in `templates/styles/`.
  Describe the craft of the era, never the condition of an old tape. Keep the
  RENDER CLEAN section: the user adds period artefacts later in DaVinci and
  baked-in ones cannot be removed.
- `_source/tail.txt` - global audio and negatives.
- `_source/content.json` - one entry per scene. `mvkit draft` seeds it from the
  screenplay; rewrite the entries into real shot language per
  `templates/drafting.txt`.
  **Write every title and description in English**, whatever language the
  screenplay and the user are in - H3 follows English shot language far more
  reliably. The `lyrics` field is the exception: verbatim, in its original
  language, never translated or tidied. So is any sung or spoken line quoted
  inside a shot.
  **Keep framing out of the action.** The camera block supplies it, and the same
  action text is reused by v1/v2/v3 verbatim, so "close-up" in the action
  contradicts two of the three. Staging that is part of the story - a focus
  rack, one character looming - does belong there.
  `mvkit build` warns about both: scenes that still read as German, and actions
  that name a framing.

### Cameras

**v1 is the director's shot, not yours.** If the screenplay states a framing,
v1 restates it. `scenes.tsv` carries what was asked for in its `framing` column;
`mvkit build` warns about any scene where v1 ignores it. Write the three per
scene in `content.json`:

```json
"cameras": {"v1": "[Static shot] Over the frog's shoulder, at the waterline ...",
            "v2": "[Static shot] The answering angle from ahead of him ...",
            "v3": "[Static shot] Close on his face just above the water ..."}
```

v2 and v3 are yours: coverage by film-theory practice - never repeat v1's shot
size, cross the axis rather than nudge it, and let one of them carry what the
master cannot. `templates/cameras/__COVERAGE.txt` has the table per v1 type, and
`__GLOSSARY.txt` the vocabulary and H3's bracket commands.

For a song with no screenplay, a whole-film set is enough:
`cp templates/cameras/rostrum-2d.txt templates/cameras.txt` (or into the song's
`_source/cameras.txt` to keep it local).

## 4. Hand over

Report: scene count, the span of song covered, which scenes were padded or
split, the reference tags, and where the deliverable is. Point at
`songs/<name>/__READ_ME.txt`, and at `docs/comfyui-batch.md` if they ask how to
render a whole song rather than one scene.

The generated `NN_*.txt` are finished six-section H3 prompts - no `#` comments,
no `@` directives. That markup is the kit's DSL and belongs only in
`ALL_scenes.txt`. Do not add it back to the per-scene files.

## Rules that break renders if you get them wrong

- Length is only valid where `frames % 17 == 5`, trained 124-362, and H3 rounds
  UP. The scenes step is the only thing allowed to choose durations.
- Max ~15 s per generation. One scene = one render.
- 9 images, 3 videos, 3 standalone audio, 12 media total. Reference tags
  renumber over what is actually connected, and a reference video's own
  soundtrack claims an `<Audio>` number before any standalone audio.
- Six sections in order: subject_definitions, summary, retention_analysis,
  detailed_description, overall_soundscape, non_diegetic_music. Internal cuts
  are `At 00:0X.XXX, cut to [Shot N]`; the first shot carries no timestamp.
- Concrete physical detail. Never "cinematic", "epic", "beautiful".
- v1/v2/v3 are coverage of one moment: the ACTION text is byte-identical across
  them and only the camera block differs. Preserve that.

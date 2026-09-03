---
name: fit-prompts
description: Shorten a song's H3 prompts until every one fits inside 7,000 characters. Use when `mvkit build` reports prompts over the limit, when a scene's prompt has to be made shorter, or when the brief and style blocks have grown. Decides which text to cut and rewrites it - the build script only measures.
---

# Get the prompts under 7,000 characters

`mvkit build` measures and names what is too long. It does not cut: choosing
which sentence carries the shot and which is padding is judgement, and a script
that truncates would cut the shot description off the end, which is the exact
failure this limit exists to avoid.

Read `CLAUDE.md` for the H3 rules before rewriting anything.

## 1. Measure

```
./mvkit build <song>
```

The report names every prompt over the limit, with its section sizes, then the
blocks that sit in **every** prompt:

```
! 2 prompt(s) over the 7000-character length H3 documents:
    01-v1  7210  (+210)
      subject_definitions 2404  summary 295  retention_analysis 578
      detailed_description 3127  overall_soundscape 402  non_diegetic_music 133
  in every prompt : [style] 883  [sound] 389  [music] 127
  per subject     : das huhn 429, der forscher 742, pond 851, ...
```

## 2. Pick the lever by how many scenes are over

- **One or two scenes.** Local problem. Cut that scene's `shot1`/`shot2` in
  `_source/content.json`. Nothing else is affected.
- **Many scenes, or the same subject in all of them.** Shared problem. Cut the
  `[subject <slug>]` or `[style]` block in `_source/brief.txt`. One edit moves
  every prompt that carries it, so take the biggest block that the over-long
  scenes have in common - the per-subject sizes in the report say which.

Prefer the local lever. A shared block is in 40 prompts and every character you
take out of it, you take out of all of them.

## 3. What must survive the cut

Never remove:

- **Scale.** Real measurements and the relations between characters ("eighteen
  times the frog", "reaches just below his knee"). The references are portraits
  that all fill their own frame; without this H3 draws a frog the size of a man.
- **The invariants.** Whatever the block says must never drift - colour model,
  markings, proportions, a costume detail that identifies the character.
- **The RENDER CLEAN section** in `[style]`. Baked-in grain cannot be removed
  later; that is the whole reason it is there.
- **Lyrics and dialogue**, verbatim and in their original language.
- **What is fixed about a location** that every shot of it must show.

Cut first:

- Adjectives that constrain nothing ("beautiful", "striking", "carefully").
- A sentence in the action that restates what `[style]` already says about the
  look - the style is in `detailed_description` of the same prompt, above it.
- Backstory and motivation in a `[subject]` block. H3 draws; it does not act.
  One behavioural rule is enough.
- Repetition between `shot1` and `shot2` of the same scene.
- Framing words in the action - they are wrong there anyway (the action is
  byte-identical across v1/v2/v3, so "close-up" contradicts two of the three),
  and the build already warns about them.

Everything stays **English** except lyrics. Concrete physical detail, never
"cinematic" or "epic".

## 4. Verify

```
./mvkit build <song>
```

Repeat until the report has no `!` line about length. Then say what you cut and
where, per scene or per block - the user has to recognise their own film in it.

Do not edit the generated `NN_*.txt` in the `set-*/` folders. They are rewritten
on every build, and an
edit there is gone by the next run.

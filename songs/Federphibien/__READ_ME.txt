FEDERPHIBIEN - 49 scenes over 171.4 s of song, 283.6 s of clip material (scenes overlap - trim in the edit)
==========================================================================

WHAT HAPPENS

  A frog loves a hen. That is the whole plot, and it is played completely straight.

  Before the music, the pond sits still: a worn sign swaying, dragonflies, reeds
  moving in the wind. A man in a straw hat is already sitting at the far edge with
  his back turned, drawing. Nobody points him out.

  The song starts high above the farm and comes down to one frog swimming across
  the pond. He hauls himself out, flops on his belly, rolls onto his back and
  begins to complain: he is sad, his skin is slimy, the flies could be lunch but he
  is not hungry. Across the yard a hen pecks grain, entirely unbothered. She lifts
  her head, judges the pond, and walks off. He is a frog, in love with a chicken,
  and their worlds do not touch - but he decides they are meant for each other
  anyway, and sets off hopping.

  While he hops he imagines the children. Federphibien: frog bodies with combs,
  slimy feathers, huge eyes, no good for flying and no good for swimming. The
  daydream curdles - the same creatures float dead in the pond - and the man at the
  water's edge turns out to be writing it all down: a scientific plate of a hen and
  a frog, and the note "Huhn + Frosch = Federphibium".

  Then he actually tries. He skids onto the gravel, runs up the chicken ladder and
  lands in a heap of down. The hen shrieks him down. He offers a gold ring in a box
  folded from lily leaves; she swallows it and walks straight past. So he throws
  grain over himself instead, and it sticks to his wet skin. That works. She stops,
  comes back, stoops, and pecks him once - gently. Their eyes meet, something lands
  with her, and she turns and offers him her back.

  They run out of the hen house together. The man at the pond jumps up, grabs his
  old camera and photographs them, still without ever showing his face. They run
  into the sunset, the hen jumps, the frog lifts off her back, and the film freezes
  on that pose.

  Nothing in it is winked at. The sincerity is the joke.

--------------------------------------------------------------------------

Every scene is one MiniMax H3 render. Files are paired by prefix:

  NN_title.mp3      the exact window of the song for that scene
  NN_title-v1.txt   wide master        }  same action, three cameras -
  NN_title-v2.txt   other angle        }  render two or three and cut
  NN_title-v3.txt   close / detail     }  between them inside the scene

The -vN.txt files are finished H3 prompts: MiniMax's six sections, no
markup, nothing to strip. Paste one in as the prompt exactly as it is.

  __SCENES.tsv      frame count, timing and pairing for every scene
  __batch/          line-aligned lists for batching in ComfyUI
  ALL_scenes.txt    the same material in this kit's DSL, which is what
                    the ComfyUI storyboard node reads for a batch run

References to load, in this order:

  <Picture 1>  federphibium (char)
  <Picture 2>  der frosch (char)
  <Picture 3>  das huhn (char)
  <Picture 4>  board (style)
  <Picture 5>  der forscher (char)
  <Picture 6>  pond (loc)
  <Picture 7>  henhouse interior (loc)
  <Audio 1>    this window of the song

Scenes that continue the shot before them:

  The screenplay holds one camera setup across these. Render them in
  order, export the LAST frame of the preceding clip, and load it as the
  first-frame reference for the next - that is what keeps the drawing from
  changing mid-setup while there are no character references.

  12_back-to-the-frog   <- last frame of 11_the-hen-turns-away
  29_she-walks-straight-past   <- last frame of 28_she-swallows-it
  31_cartoon-hearts   <- last frame of 30_her-walk
  35_she-pecks-him   <- last frame of 34_she-stoops-down

Scenes that must end on the frame they started on (the screenplay
marks them First Frame <> Last Frame): 11, 14, 24, 31, 35, 47


COMPOSITING - assembled in the edit, not rendered in

  16_hopping-through-the-grass  [loop]
        the open upper half is where scenes 15, 17 and 18 are placed
        the screenplay's endlose Loop: butt-join the clip to itself to
        hold the hop for as long as the visions need
  14_in-love-with-a-chicken  [plate]
        upper left of the sky, half transparent: the hen seen in profile
        the screenplay says oben links. The element is generated:
        90_hen-profile-element, same 226 frames as this plate.
  15_imagine-our-children  [inset] -> over 16
        into the open sky in the upper half of scene 16, half transparent
        one of the three Zukunftsvisionen - the hen crocheting while three
        Federphibien play
  17_slimy-feathers  [inset] -> over 16
        into the open sky in the upper half of scene 16, half transparent
        one of the three Zukunftsvisionen - the slime-soaked feathers
  18_great-big-eyes  [inset] -> over 16
        into the open sky in the upper half of scene 16, half transparent
        one of the three Zukunftsvisionen - the huge eyes
  90_hen-profile-element  [element] -> over 14
        upper left of the empty sky in scene 14, half transparent
        no audio and no place on the timeline - hold or loop it to taste.
        Blend mode over the plate's flat sky; her grey field is meant to
        disappear.
  47_the-final-freeze  [freeze]
        hold the last frame as long as you like, then close the iris in
        Resolve - the screenplay asks for the effect there, so it is not
        rendered in

  A plate is rendered with its overlay area left empty on purpose.
  An inset or element is a full-frame clip of its own - place, scale
  and fade it in the edit. An element has no audio and no place on the
  timeline; it exists only to be laid over something.
  Nothing here is burned into a render.


RENDERING THIS FOLDER IN COMFYUI

  This folder is finished. ComfyUI never needs the pdf or the whole mp3 - the
  screenplay, the transcript and the audio split all happen in the kit, and what
  arrives here is already paired: one prompt and one slice per scene, with the
  frame count each scene must be rendered at.

  TWO WORKFLOWS IN THIS FOLDER

    __workflow_song.json     the render. YOUR H3 graph with this folder wired in.
    __workflow_upscale.json  the pass afterwards. No H3 in it.

    Nothing here tries to invent a render graph. The H3 node returns `positive`
    and `LATENT` - it conditions a sampler and hands back no video - so a
    complete graph needs a model loader, CLIP and VAE loaders, a sampler, two
    VAE decodes and a CreateVideo behind it. None of that can be guessed, and
    ComfyUI already ships the whole thing under Workflow -> Browse Templates.

    So: get the official ref2va template rendering ONE scene, save it, and

      ./mvkit workflows Federphibien --from <that file>

    Either format works - a workflow saved from the menu is converted to API
    format on the way in. What it does:

      - keeps every node and setting you had: loaders, sampler, scheduler,
        LoRA switches, resolution, the audio decode path, your Save node
      - rewires only `prompt` and `length` to this folder's scene
      - puts this scene's slice on `ref_audios.ref_audio_0`
      - fills `ref_images.ref_image_0..n` from _source/refs/, each loader
        TITLED with its live tag, e.g. "<Picture 3> das huhn (char)"
      - drives your Save node's `filename_prefix` from save_prefix
      - prints what it rewired, and warns if your node has fewer ref_image
        slots than the song has sheets

    CONNECT AS MANY ref_image SLOTS AS YOU HAVE SHEETS FIRST. They are dynamic:
    one appears as you fill the last. Wrap seven sheets into a node with one slot
    and six are dropped - it says so, but it cannot invent inputs.

    NO ABSOLUTE PATHS ARE WRITTEN. ComfyUI usually runs somewhere else than this
    kit - another machine, another OS - so `song_path` is left EMPTY and the node
    is titled to say so. Set it once to where this folder lives on the ComfyUI
    machine. The build refuses to write a graph containing an absolute path.

    Then: `scene_index` to `increment`, batch count to `scene_count`, Run once.

  THE OTHER WAY - drive it from outside

    If you would rather not install anything, `mvkit queue` posts one job per
    scene to ComfyUI's HTTP API and needs no node from this kit:

      ./mvkit queue Federphibien wf_api.json --dry-run
      ./mvkit queue Federphibien wf_api.json

    Export the graph with Workflow -> Export (API), not the normal save, and
    title the nodes it should drive PROMPT, AUDIO and LENGTH. `mvkit probe` tells
    you which node to give which title - two roles often sit on the H3 node
    itself, and a node has only one title, so it matters. The dry run prints what
    it matched and what it would send; read it first.

    Flags: --variant v2, --scenes 1-10,15, COMFY_HOST for another machine.

  WHY NOT ONE BATCH FOR EVERYTHING

    H3 only accepts lengths where frames % 17 == 5 and there is one `length` per
    queue run, so in-graph batching needs one run per frame count. Both routes
    above set the length per scene instead, which is why they manage the whole
    song in one pass. __batch/ still holds the grouped lists if you want the
    node-pack route; see docs/comfyui-batch.md.

  Scene 00 and any 90+ scene have no audio - the Vorspann and the compositing
  elements. Both routes handle them: the audio input is simply left alone. They
  are deliberately absent from __batch/, which pairs prompts with slices line by
  line and cannot carry a clip that has no slice.

  UPSCALING, AFTERWARDS - __workflow_upscale.json

    A separate graph with no H3 in it at all. It is the pass you run once the
    renders exist and you have thrown out the takes you do not want:

      Hurricane Clip Folder ─► Load Video (Path) ─► Upscale 4x ─► scale to 2560x1440
       (source_dir)                    └─ audio ──────────────────────┐
                                                                Video Combine
                                                                (out_subfolder)

    0. copy comfyui/custom_nodes/watching_hurricanes_upscale.py into
       ComfyUI/custom_nodes/ - it is a separate file from the storyboard
       nodes and needs neither the other nor any dependency.
    1. put the pruned folder in `source_dir`. It lists what is ACTUALLY there,
       so a take you deleted is simply not in the run.
    2. read `clip_count` off the node, set `clip_index` to `increment` and the
       queue's batch count to exactly that number. Too high is an error rather
       than a silent re-render of the last clip - which is what you want when it
       runs unattended.
    3. Run once and leave it.

    Clips keep their own names: 01_the-pond-from-above-v1.mp4 comes out as
    <out_subfolder>/01_the-pond-from-above-v1.mp4, so the pairing with the prompt
    survives and `mvkit concat` still reads them in scene order. Audio rides
    through untouched.

    ONE 4x MODEL, NO RESCALING. The graph writes exactly what the model
    produces - there is no scaling node after it. So the output is 4x the render:
    4x off 540p is 3840x2160, off 720p it is 5120x2880, off 1080p it is 8K. Only
    the 540p case lands on 4K on the nose; correct the rest in DaVinci, which
    scales better than a second model pass would anyway.

    The model is RealESRGAN_x4plus_anime_6B - trained on line art, keeps a hard
    ink outline where a photo model smears it. Put the .pth in
    ComfyUI/models/upscale_models/. Alternatives if it is too soft or too sharp:
    4x-AnimeSharp (sharper), DigitalFrames 2.0 (trained on cel/film toons - not
    the 2.1_Aggressive variant).

    Mind the size: 8K frames eat VRAM and disk, and crf 12 on the combine keeps
    quality high, which also means large files.

    NOT a diffusion upscaler, on purpose. This picture is a black line and flat
    washes - there is no hidden detail to reconstruct, so a generative model
    invents texture in areas that must stay flat, and invents it differently in
    every frame. On flat colour that shimmer is far more visible than on
    photographic footage, and it is exactly what RENDER CLEAN exists to prevent.
    An ESRGAN-class model is deterministic: same pixels in, same pixels out, so it
    is temporally stable without any extra setting.

    Alternative worth trying first: DaVinci Resolve Studio's Super Scale (Clip
    Attributes, 2x) hallucinates nothing, is already in your pipeline and costs no
    ComfyUI work at all.

    TWO CONNECTIONS TO CHECK ONCE. VideoHelperSuite has renamed things between
    versions, so verify in the UI that Load Video (Path)'s third output really is
    AUDIO, and that `force_size` still exists on it (newer builds use
    custom_width/custom_height instead). Everything else in the graph is stable.


Set length to the frame count in __SCENES.tsv - H3 only accepts lengths
where frames % 17 == 5, and it rounds up, so do not retype it by feel.

Do not edit these files - they are regenerated. Edit _source/ and re-run
`mvkit build Federphibien`.

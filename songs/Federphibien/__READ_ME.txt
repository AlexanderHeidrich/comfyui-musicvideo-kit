FEDERPHIBIEN - 49 scenes over 171.4 s of song, 288.6 s of clip material (scenes overlap - trim in the edit)
==========================================================================

WHAT HAPPENS

  A frog loves a hen. That is the whole plot, and it is played completely straight.

  Before the music, the titles run over an aerial from flying height: scattered
  summer cloud drifting past, farmland below, and in one gap a single farm small
  enough to cover with a thumbnail. Nothing down there is big enough to see.

  The song starts on that last frame and the camera drops out of the sky onto the
  pond, where one frog is swimming across it. He hauls himself out, flops on his belly, rolls onto his back and
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
  NN_title-v1.txt   the director's shot
  NN_title-v2.txt   other angle, medium
  NN_title-v3.txt   close / detail

WHAT EACH VERSION IS FOR

  v1  YOURS. Whatever framing the screenplay states is what v1 does -
      `mvkit scenes` lifts it out of the Drehbuch into the framing column
      and the build warns when v1 ignores it. If the screenplay says
      over-the-shoulder at water level, that is v1. It is the shot you
      wrote, not an interpretation of it.

  v2  and
  v3  COVERAGE, chosen by film practice rather than by the screenplay:
      never repeat v1's size, cross the axis so the two cut together,
      and give one of them something the master cannot hold - a face, a
      hand, a point of contact. v2 is roughly ninety degrees off the
      master and closer, v3 is the detail. See
      templates/cameras/__COVERAGE.txt for the table they come from.

      The ACTION text is byte-identical in v1, v2 and v3 - only the
      camera differs. That is the point: they are three angles on ONE
      moment, they share the single NN_title.mp3, and they can be cut
      together inside the scene. They are not alternative takes.

  v4  THE SHORT BUILD, and an experiment. Same shot as v1, same camera,
      same references - but assembled from _source/brief.txt instead of
      the full bible and style, and carrying only the characters that are
      actually in the scene. Roughly 6 KB against v1's 30 KB.
      Every published H3 guide puts the prompt limit at 7,000 characters.
      If that limit is real for ComfyUI too, then in v1 the model never
      reaches the shot description at all - it stops inside the cast list
      and improvises the rest, which is what stray characters and
      vanishing scenery look like. UNTESTED. Render 01-v4 against 01-v1
      and compare before believing either of them.

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

  01_the-pond-from-above   <- last frame of 00_high-above-the-farm
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
        Blend mode over the plate's flat sky; her flat blue field is meant
        to disappear.
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

  THE WORKFLOWS IN THIS FOLDER

    Federphibien.json        the render. YOUR H3 graph with this folder wired in, your
                       layout and groups kept. UI format - open this one.
    Federphibien-api.json    the same in API format, for `mvkit queue`. No layout,
                       because that format has no positions at all.
    Federphibien-4x.json     the upscale pass afterwards. No H3 in it.

    Nothing here invents a render graph. The H3 node returns `positive` and
    `LATENT` - it conditions a sampler and hands back no video - so a working
    graph needs a UNET loader, CLIP and VAE loaders, a sampler, a VAEDecode AND a
    VAEDecodeAudio, and a CreateVideo behind it. ComfyUI ships that whole chain
    under Workflow -> Browse Templates. Get it rendering ONE scene, save it, then

      ./mvkit workflows Federphibien --from <that file>

    and it grafts this folder in: your loaders, sampler, scheduler, LoRA switches,
    resolution and Save node all stay, and only four things get rewired -
    `prompt`, `length`, `ref_audios.ref_audio_0` and your Save node's
    `filename_prefix`. The reference sheets are left completely alone, because
    they are identical in every scene of the song; their loaders only get retitled
    with their live tag, e.g. "<Picture 3> das huhn (char)".

    ONE NODE, FOUR OUTPUTS. Hurricane Song Folder hands out only what changes from
    scene to scene:

      prompt        the finished six-section prompt for this scene
      audio_path    this scene's slice, for a Load Audio (Path)
      frames        the frame count, straight onto H3's `length`
      scene_count   what to set the queue's batch count to
      save_prefix   "<song>/NN_slug-vN", so renders arrive named and grouped

    NO ABSOLUTE PATHS ARE WRITTEN. ComfyUI usually runs somewhere else than this
    kit, so `song_path` is left EMPTY and the node is titled to say so. Set it once
    to where this folder lives on the ComfyUI machine. The build refuses to write a
    graph containing an absolute path.

    EVERY SCENE HAS AUDIO, including the ones with no window of the song. The
    Vorspann and the compositing elements get a slice of SILENCE of exactly the
    right length, because an empty audio path is what an audio loader chokes on -
    it took down the first job of a batch run. So the batch is simply every scene:
    no special cases, no bypassing.

    For the next song you need not wrap again - copy this file and change
    `song_path`.

  WHICH WEIGHTS GO WHERE

    There is nothing to tune here - each slot has exactly one right answer:

      UNET       minimax_h3_ref2va_pruned_int8_convrot     reference -> video+audio
      CLIP       qwen3vl_..._minimax_h3_...                the only one that fits
      vae        minimax_h3_video_vae_fp16                 the picture
      audio_vae  minimax_h3_audio_vae_fp32                 the sound

    `pixel_space` in the VAE list is ComfyUI's "no VAE" entry, not a file. The
    fp16/fp32 split is how these ship, not a mistake.

    THE OTHER H3 MODEL IS FOR THE CHAINED SCENES. `minimax_h3_fl2va` is
    first-and-last-frame to video, and __SCENES.tsv marks some scenes `chain` in
    the continuity column: they have to continue off the previous clip's last
    frame, and ref2va has no way to do that - it only knows reference images. For
    those, render the run in order with fl2va, feeding each clip's last frame in
    as the first frame of the next. The prompt and the slice from this folder stay
    the same; only the model and that one input differ.

  CHECK THE RESOLUTION BEFORE THE LONG RUN

    If your graph gets width/height from a ResolutionSelector, look at its
    `megapixels`. H3's own widget defaults are 1344x768, which is 1.03 MP - a
    selector left at 0.4 MP renders 832x480 instead, and you will not notice
    until you compare. 16:9 at multiple=32:

      megapixels 0.4  ->  832x480      1.0  -> 1344x736
                 0.6  -> 1024x576      1.03 -> 1344x768   (H3's default)

    It also decides where upscaling lands: 480 lines times four is 1920, not 4K.

  RUNNING THE WHOLE SONG - one press of Run

    1. set `song_path` to where this folder lives on the ComfyUI machine
    2. click the arrows beside `scene_index` and set its control to `increment`
    3. set the queue's **Batch count** (the number next to Run, not a widget) to
       the node's `scene_count` output. That is NOT the number of rows in
       __SCENES.tsv: `include` defaults to "scenes with audio", which leaves out
       scene 00 and anything numbered 90+ because they have no window of the song
       and an audio loader wired to audio_path would throw on them. Those are
       rendered separately - set `include` to "only scenes without audio" and
       bypass the audio loader (Ctrl+B) for that short run.
    4. press Run ONCE

    You see each result as it lands, not at the end. Every queued job is its own
    execution, so Save Video writes that scene's file the moment it finishes and
    the node shows it. Watch the first one or two, and abort the queue if the look
    is wrong - that is the whole reason to check scene 1 before committing 49.

    ComfyUI queues that many jobs and steps `scene_index` up by one for each. You
    do not touch anything in between. A count set too high is an error rather
    than a silent re-render of the last scene, so getting it wrong costs you a
    message and not a night.

    The reference sheets are NOT driven per scene - they are the same in every
    scene, so their loaders keep their own filenames and are only retitled with
    their live tag. Only the prompt, the frame count and the audio slice change.

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

    GETTING THE MODEL. Exact filename, and it is a .pth - ComfyUI loads those for
    upscalers, no conversion needed:

      RealESRGAN_x4plus_anime_6B.pth      (17 MB)
      https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth

    Drop it in  <your ComfyUI>/models/upscale_models/  and refresh the browser
    (or hit the refresh button) - the model_name dropdown is built from that
    folder when the UI loads, so a file added while it is open will not show up
    until you do.

    The graph already names it, so once the file is there the two nodes resolve
    on their own: Load Upscale Model (UpscaleModelLoader) feeds Upscale Image
    (using Model) (ImageUpscaleWithModel).

    Alternatives if it comes out too soft or too sharp: 4x-AnimeSharp (sharper),
    DigitalFrames 2.0 (trained on cel/film toons - not the 2.1_Aggressive
    variant). Both are on openmodeldb.info and go in the same folder.

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

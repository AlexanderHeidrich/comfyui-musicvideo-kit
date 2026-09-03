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

Every scene is one MiniMax H3 render. The scenes live in the set-*
folders, grouped by the reference sheets they need, and inside one of
those the files are paired by prefix:

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

All three are built from _source/brief.txt and carry only the
characters the scene actually contains, so they stay inside the 7,000
characters MiniMax documents as the prompt length.

The -vN.txt files are finished H3 prompts: MiniMax's six sections, no
markup, nothing to strip. Paste one in as the prompt exactly as it is.

  __SCENES.tsv      frame count, timing and pairing for every scene
                    of the whole song, and which set folder each one
                    is in

References to load, in this order:

  <Picture 1>  federphibium (char)
  <Picture 2>  der frosch (char)
  <Picture 3>  das huhn (char)
  <Picture 4>  board (style)
  <Picture 5>  der forscher (char)
  <Picture 6>  pond (loc)
  <Picture 7>  henhouse interior (loc)
  <Audio 1>    this window of the song

  Those are the sheet numbers, not the tags a scene uses. A scene
  carries only the sheets it contains - the `refs` column of
  __SCENES.tsv says which - and H3 numbers what it is handed, so
  <Picture 1> means something different from set to set.

--------------------------------------------------------------------------

ONE FOLDER AND ONE GRAPH PER REFERENCE SET

Every scene in one of these folders is handed exactly the same
reference sheets, so a graph for it needs only those sheets and needs
them in one fixed order. That is the whole point: no sheet is
connected that the scene does not contain, and <Picture 1> in a
prompt is the first sheet the graph loads.

You render a song by working through these folders, one graph each.
Each folder IS a song folder and carries everything it needs - the
prompts, the mp3s and its own __SCENES.tsv - so switching sets is
pointing song_path at the next folder. Set scene_index to increment
and the queue's batch count to that folder's scene_count.

The graphs are written by

    ./mvkit workflows Federphibien --from <your saved workflow.json>

which keeps your sampler, loaders and layout and throws out the
image loaders a set does not use.

WORK LIST - the graph in each folder is named after it

    folder                     sheets         scenes which

[ ] set-01_2-3-4               2,3,4          11     10 26 28 31 33 35 37 38 41 45 47
[ ] set-02_2-3-4-7             2,3,4,7        10     23 24 25 29 30 34 36 39 40 42
[ ] set-03_2-4-6               2,4,6          6      02 05 06 12 16 21
[ ] set-04_2-4-6-7             2,4,6,7        3      04 14 27
[ ] set-05_3-4-6               3,4,6          3      09 11 90
[ ] set-06_2-4                 2,4            2      07 22
[ ] set-07_2-4-5-6-7           2,4,5,6,7      2      03 08
[ ] set-08_2-4-7               2,4,7          2      13 32
[ ] set-09_1-3-4-6             1,3,4,6        1      15
[ ] set-10_1-4                 1,4            1      18
[ ] set-11_1-4-5-6             1,4,5,6        1      19
[ ] set-12_1-4-7               1,4,7          1      17
[ ] set-13_2-3-4-5             2,3,4,5        1      44
[ ] set-14_2-3-4-5-6           2,3,4,5,6      1      43
[ ] set-15_2-3-4-6             2,3,4,6        1      46
[ ] set-16_2-4-5-6             2,4,5,6        1      01
[ ] set-17_4-5-7               4,5,7          1      20
[ ] set-18_4-6-7               4,6,7          1      00

`scenes` is the batch count for that folder, and the node's
scene_count output says the same thing - use that one.

The sheet numbers are the ones listed above, in that order. A prompt
numbers them 1..n over its own set: in a set of sheets 2,4,7 the
prompts say <Picture 1>, <Picture 2>, <Picture 3>, and that set's
graph loads them in exactly that order. That is why a set folder and
its graph belong together and are not interchangeable.

--------------------------------------------------------------------------


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

  YOU RENDER FROM THE set-* FOLDERS

    A picture H3 can see is a picture H3 uses. "Do not use <Picture 5>" in the
    prompt does not stop it turning up as the first frame, so a sheet a scene does
    not contain must not be connected at all - and a saved graph cannot change how
    many links it has from scene to scene. So the scenes are grouped by the set of
    sheets they need, and each set gets its own folder and its own graph:

      set-NN_<sheets>/                  one folder per set, self-contained:
        <this song>-set-NN_<sheets>.json  the graph, carrying only those sheets
        __SCENES.tsv                      only that set's scenes
        NN_title-v1/v2/v3.txt             their prompts
        NN_title.mp3                      their slices

    The work list at the end of this file says which set, how many scenes and
    which scenes. Work through it folder by folder.

    A prompt numbers the sheets of its own set - <Picture 1> is the first sheet
    ITS graph loads, not sheet 1 of the song - so a folder and its graph belong
    together and cannot be mixed with another set's.

  THE WORKFLOWS

    set-*/Federphibien-set-*.json   the renders, one per set. Open one, point
                       song_path at the folder it sits in, run, move on.
    Federphibien-4x.json     the upscale pass afterwards. No H3 in it.

    Nothing here invents a render graph. The H3 node returns `positive` and
    `LATENT` - it conditions a sampler and hands back no video - so a working
    graph needs a UNET loader, CLIP and VAE loaders, a sampler, a VAEDecode AND a
    VAEDecodeAudio, and a CreateVideo behind it. ComfyUI ships that whole chain
    under Workflow -> Browse Templates. Get it rendering ONE scene, save it, then

      ./mvkit workflows Federphibien --from <that file>

    and it writes ONE GRAPH PER SET from it. Your loaders, sampler, scheduler,
    LoRA switches, resolution and Save node all stay; rewired are `prompt`,
    `length`, `ref_audios.ref_audio_0` and your Save node's `filename_prefix`, and
    the image loaders a set does not need are removed. The rest are retitled with
    the number the prompts use, e.g. "<Picture 2> - das huhn (char)  [sheet 3]".

    Connect the sheets in the order __READ_ME.txt lists them before you save: that
    order is how the graft knows which loader is which sheet.

    The graph you grafted from is kept as _source/workflow.json, and every
    `mvkit build` re-grafts all the set graphs from it - which it has to, because
    a build rewrites the set folders from scratch. Change your graph, save it,
    run `mvkit workflows ... --from` once more.

    ONE NODE. Hurricane Song Folder hands out what changes from scene to scene:

      prompt        the finished six-section prompt for this scene
      audio_path    this scene's slice, for a Load Audio (Path)
      frames        the frame count, straight onto H3's `length`
      scene_count   what to set the queue's batch count to
      save_prefix   "<song>/NN_slug-vN", so renders arrive named and grouped

    The renders of every set land in the same output folder, named after the
    scene, so the song comes back together on its own.

    NO ABSOLUTE PATHS ARE WRITTEN. ComfyUI usually runs somewhere else than this
    kit, so `song_path` is left EMPTY and the node is titled to say so. Set it once
    to where this folder lives on the ComfyUI machine. The build refuses to write a
    graph containing an absolute path.

    EVERY SCENE HAS AUDIO, including the ones with no window of the song. The
    Vorspann and the compositing elements get a slice of SILENCE of exactly the
    right length, because an empty audio path is what an audio loader chokes on -
    it took down the first job of a batch run. So the batch is simply every scene:
    no special cases, no bypassing.

    For the next set you need not graft again - the graphs are already written.
    Open the next one and point it at its own folder.

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

    1. set `song_path` to where that SET folder lives on the ComfyUI machine
       (set-NN_..., not this folder)
    2. click the arrows beside `scene_index` and set its control to `increment`
    3. set the queue's **Batch count** (the number next to Run, not a widget) to
       that folder's `scene_count` output - the number of scenes in THAT SET, not
       in the song. Every scene has audio, silence included, so there are no
       special cases to leave out.
    4. press Run ONCE

    You see each result as it lands, not at the end. Every queued job is its own
    execution, so Save Video writes that scene's file the moment it finishes and
    the node shows it. Watch the first one or two, and abort the queue if the look
    is wrong - that is the whole reason to check scene 1 before committing 49.

    ComfyUI queues that many jobs and steps `scene_index` up by one for each. You
    do not touch anything in between. A count set too high is an error rather
    than a silent re-render of the last scene, so getting it wrong costs you a
    message and not a night.

    Within one set folder the reference sheets never change - that is what a set
    is. Only the prompt, the frame count and the audio slice change from scene to
    scene, which is exactly what the node hands out.

  WHY NOT ONE BATCH FOR EVERYTHING

    H3 only accepts lengths where frames % 17 == 5 and there is one `length` per
    queue run, so in-graph batching over a fixed list needs one run per frame
    count. The Hurricane node sets the length per scene instead, which is why it
    manages a whole set in one pass. See docs/comfyui-batch.md for why core
    ComfyUI cannot do it alone.

  Scene 00 and any 90+ scene have no window of the song - the Vorspann and the
  compositing elements. They get a slice of silence, so they render like any other
  scene in whichever set they belong to.

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

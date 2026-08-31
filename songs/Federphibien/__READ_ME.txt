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

  THREE STARTING WORKFLOWS ARE IN THIS FOLDER

    `mvkit build` writes them every time, so they always match the scenes beside
    them. All three are API-format graphs - open them with Workflow -> Open.

      __wf_1_scene.json     one scene, everything explicit and pre-filled. Every
                            reference loader is TITLED with its live tag, e.g.
                            "<Picture 3> das huhn (char)", so the graph itself
                            says which image is which. Good for getting the H3
                            node right the first time.
      __wf_2_folder.json    the one you want. Hurricane Song Folder reads this folder
                            and drives everything.
      __wf_3_pipeline.json  Hurricane Build Song runs ./mvkit on the host first, then
                            the same. For when you want one button.

    First, once: copy (or symlink) comfyui/custom_nodes/watching_hurricanes.py into your
    own ComfyUI/custom_nodes/ and restart. Stdlib only, nothing to install.

    Then, because the H3 node's class name cannot be known without asking:

      ./mvkit probe --song Federphibien --emit

    That reads /object_info off the running server and rewrites all three with
    the class names it actually reports. Until you run it the H3 node may show as
    missing - that is the placeholder, not a broken graph.

    __wf_2_folder.json is wired like this:

      Hurricane Song Folder ──► prompt      ──► H3 ref2vid ──► Save Video
       (song_path)   ──► frames      ──►
                     ──► audio_path  ──► Load Audio (Path) ──►
                     ──► ref_1..ref_n ─► image loaders, titled by tag ──►

    Open it, finish the H3 node's own settings, render ONE scene. Then set MV
    Song Folder's `scene_index` to `increment`, set the queue's batch count to
    its `scene_count` output, and press Run once. That is the whole song.

    `variant` picks v1, v2 or v3. Paths come out of the node as strings because
    turning a file into ComfyUI's IMAGE/AUDIO types needs torch, and that file
    deliberately has no dependencies.

  WHERE THE CLIPS END UP

    Renders are NOT temporary. Save Video writes into ComfyUI/output and the
    files stay there; what does get cleared is anything from a Preview node,
    which writes to ComfyUI/temp. If your clips seem to vanish between sessions,
    check that the end of your graph is a Save and not a Preview.

    What was missing is a name. Hurricane Song Folder has a `save_prefix` output
    that the generated graphs wire into Save Video's `filename_prefix`, so each
    clip lands as

      ComfyUI/output/Federphibien/NN_slug-vN_00001.mp4

    grouped per song and named after the prompt that made it - which is what
    `mvkit concat` wants to see. Put something in `out_subfolder` to change the
    first part (e.g. "Renders/take2") and the rest follows.

    ComfyUI will not write outside its own output folder; that is its path
    sanitising, not our choice. Point `out_subfolder` where you want it inside
    output, then collect from there.

  WRAPPING YOUR OWN H3 WORKFLOW

    The generated graphs guess nothing about your model, resolution or account,
    so once you have an H3 ref2vid graph that renders the way you want it, keep
    it and let the kit wrap that instead:

      ./mvkit workflows Federphibien --from my_h3_export.json

    That writes __wf_4_wrapped.json: your graph untouched except for the four
    inputs a song folder drives - prompt, length, audio and the image slots -
    plus the save prefix at the back. Every other setting on your H3 node is
    left exactly as you had it. It prints what it rewired and warns when your
    node has fewer image slots than the song has reference sheets.

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

  UPSCALING, AFTERWARDS - __wf_5_upscale.json

    A separate graph with no H3 in it at all. It is the pass you run once the
    renders exist and you have thrown out the takes you do not want:

      Hurricane Clip Folder ─► Load Video (Path) ─► Upscale 4x ─► scale to 2560x1440
       (source_dir)                    └─ audio ──────────────────────┐
                                                                Video Combine
                                                                (out_subfolder)

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

    WHY A 4x MODEL AND THEN DOWN. RealESRGAN_x4plus_anime_6B is trained on line
    art and keeps a hard ink outline where a photo model smears it. The 4x models
    are better trained than the 2x ones, and scaling back down to the target takes
    the over-sharpening out again. Put the .pth in ComfyUI/models/upscale_models/.

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

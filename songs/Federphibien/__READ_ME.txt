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


RENDERING THE WHOLE FOLDER IN ONE RUN

  The fast path does not batch inside the graph at all - it posts one job per
  scene over ComfyUI's HTTP API, reading this folder directly. Every scene keeps
  its own frame count that way, which in-graph batching cannot do: H3 only
  accepts lengths where frames % 17 == 5, so one `length` per queue run means
  one run per frame count.

  Once:
    1. copy mv_h3_nodes.py into ComfyUI/custom_nodes/ and restart ComfyUI
    2. build a graph for ONE scene and get it rendering
    3. rename three nodes by double-clicking their title bars:
         PROMPT   the text node feeding the H3 prompt
         AUDIO    the node that loads an audio file by path
         LENGTH   the int feeding `length`
    4. Workflow -> Export (API). Not the normal save - the API format is a flat
       map of node ids, and the normal save is rejected with a message saying so.

  Then, every time:
    ./mvkit queue Federphibien wf_api.json --dry-run
    ./mvkit queue Federphibien wf_api.json

  The dry run prints which node each title matched and lists every scene with
  its frame count and audio file. Read it before the real run: a title that
  matched nothing is reported, not guessed at.

  Useful flags:
    --variant v2        render the coverage instead of the masters (default v1)
    --scenes 1-10,15    a subset, by scene number
    COMFY_HOST=...      another machine (default http://127.0.0.1:8188)

  Scene 00 and any 90+ scene have no audio - they are the Vorspann and the
  compositing elements. The API path queues them with the audio input left
  alone. They are deliberately absent from __batch/, which pairs prompts with
  slices line by line and so cannot carry a clip that has no slice.

  If you would rather batch inside the graph, __batch/ holds prompt and audio
  lists grouped by frame count, one pair per group, line-for-line aligned. That
  needs VideoHelperSuite and WAS Node Suite, and one queue run per group with
  `length` typed from __batch/__README.txt. See docs/comfyui-batch.md.


Set length to the frame count in __SCENES.tsv - H3 only accepts lengths
where frames % 17 == 5, and it rounds up, so do not retype it by feel.

Do not edit these files - they are regenerated. Edit _source/ and re-run
`mvkit build Federphibien`.

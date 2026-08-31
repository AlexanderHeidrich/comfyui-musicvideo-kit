FEDERPHIBIEN - 48 scenes over 171.4 s of song, 274.2 s of clip material (scenes overlap - trim in the edit)
==========================================================================

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


Set length to the frame count in __SCENES.tsv - H3 only accepts lengths
where frames %% 17 == 5, and it rounds up, so do not retype it by feel.

Do not edit these files - they are regenerated. Edit _source/ and re-run
`mvkit build Federphibien`.

Reference images and clips. The filename decides what the reference IS and in
which order H3 loads it, so stick to the schema:

  [NN_]char_<slug>.png     a character           -> <Picture n>
  [NN_]style_<slug>.png    a look / colour board -> <Picture n>
  [NN_]loc_<slug>.png      a location or set     -> <Picture n>
  [NN_]prop_<slug>.png     a prop                -> <Picture n>
  [NN_]video_<slug>.mp4    a motion reference    -> <Video n>

NN is optional and only sets load order (01_ first). Limits: 9 images,
3 videos, 12 media in total, and at least one image or video - H3 rejects
audio-only input. Run `mvkit refs <song>` to see the tags it will actually get.

Federphibien - 51 scenes in 12 reference sets
==========================================================================

Every clip is 243 frames (10.125 s). Set the H3 node's length to 243
once; it never changes. There is no audio reference and no audio in
these folders - lay the song under the picture in the edit.

__TIMELINE.tsv is the edit list: one row per scene with the
timecode it starts at, how long it holds (dur_s - mostly less
than the 10.125 s rendered, so trim), the track, and the render
the clip comes from. It is laid out at 24 fps off the Drehbuch's
own frame numbers, so the film starts at 00:00:00:00 and DROP
THE MP3 AT 00:00:10:00 - the frames before that are the
Vorspann. A V2 row is a layer over the V1 clip underneath it,
not a cut.

ComfyUI appends its own counter, so the render column names a
prefix: set-NN_x/07_slug-v1 lands as 07_slug-v1_00001_.mp4, and
-v2/-v3 are the same moment from another angle.

BEFORE ANYTHING ELSE: copy every png in this song's refs/ folder into
your ComfyUI/input/ directory. ComfyUI's LoadImage only ever reads
from there, and the graphs name the sheets by bare filename on purpose
so they keep working on whatever machine ComfyUI runs on. Without that
copy, every loader comes up empty.

AND copy comfyui/custom_nodes/watching_hurricanes.py over the one in
your ComfyUI/custom_nodes/, then restart it. The graphs wire that
node's outputs by index, so an older copy shifts every link past the
change: `mvkit probe` compares the two and says so.

Each set-*/ folder is a song folder in its own right: open its graph,
put that folder's own path into HurricaneSongFolder's song_path - it
is left empty on purpose, because no absolute path is ever written
into a graph - then set scene_index to increment and the queue's batch
count to scene_count, and press Run once.

WIRE THE LOADERS IN THE ORDER LISTED. H3 numbers <Picture n> over the
slots actually connected, so a gap shifts every tag after it and the
prompts stop matching.

set-01_2-5   (14 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  05_loc_pond.png

set-02_2-3-6   (13 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png
    ref_image_2   <Picture 3>  06_loc_henhouse-interior.png

set-03_2-3-5   (10 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png
    ref_image_2   <Picture 3>  05_loc_pond.png

set-04_2-6   (3 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  06_loc_henhouse-interior.png

set-05_3-5   (2 scenes)
    ref_image_0   <Picture 1>  03_char_das-huhn.png
    ref_image_1   <Picture 2>  05_loc_pond.png

set-06_4-5   (2 scenes)
    ref_image_0   <Picture 1>  04_char_der-forscher.png
    ref_image_1   <Picture 2>  05_loc_pond.png

set-07_1   (2 scenes)
    ref_image_0   <Picture 1>  01_char_federphibium.png

set-08_3-6   (1 scene)
    ref_image_0   <Picture 1>  03_char_das-huhn.png
    ref_image_1   <Picture 2>  06_loc_henhouse-interior.png

set-09_2-3-4-5   (1 scene)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png
    ref_image_2   <Picture 3>  04_char_der-forscher.png
    ref_image_3   <Picture 4>  05_loc_pond.png

set-10_1-3   (1 scene)
    ref_image_0   <Picture 1>  01_char_federphibium.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png

set-11_1-4-5   (1 scene)
    ref_image_0   <Picture 1>  01_char_federphibium.png
    ref_image_1   <Picture 2>  04_char_der-forscher.png
    ref_image_2   <Picture 3>  05_loc_pond.png

set-12_5   (1 scene)
    ref_image_0   <Picture 1>  05_loc_pond.png


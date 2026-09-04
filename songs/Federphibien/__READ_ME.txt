Federphibien - 51 scenes in 12 reference sets
==========================================================================

Every clip is 243 frames (10.125 s). Set the H3 node's length to 243
once; it never changes. There is no audio reference and no audio in
these folders - lay the song under the picture in the edit.

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

set-01_2-4-6   (14 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  04_style_board.png
    ref_image_2   <Picture 3>  06_loc_pond.png

set-02_2-3-4-7   (13 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png
    ref_image_2   <Picture 3>  04_style_board.png
    ref_image_3   <Picture 4>  07_loc_henhouse-interior.png

set-03_2-3-4-6   (10 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png
    ref_image_2   <Picture 3>  04_style_board.png
    ref_image_3   <Picture 4>  06_loc_pond.png

set-04_2-4-7   (3 scenes)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  04_style_board.png
    ref_image_2   <Picture 3>  07_loc_henhouse-interior.png

set-05_4-5-6   (2 scenes)
    ref_image_0   <Picture 1>  04_style_board.png
    ref_image_1   <Picture 2>  05_char_der-forscher.png
    ref_image_2   <Picture 3>  06_loc_pond.png

set-06_3-4-6   (2 scenes)
    ref_image_0   <Picture 1>  03_char_das-huhn.png
    ref_image_1   <Picture 2>  04_style_board.png
    ref_image_2   <Picture 3>  06_loc_pond.png

set-07_1-4   (2 scenes)
    ref_image_0   <Picture 1>  01_char_federphibium.png
    ref_image_1   <Picture 2>  04_style_board.png

set-08_4-6   (1 scene)
    ref_image_0   <Picture 1>  04_style_board.png
    ref_image_1   <Picture 2>  06_loc_pond.png

set-09_3-4-7   (1 scene)
    ref_image_0   <Picture 1>  03_char_das-huhn.png
    ref_image_1   <Picture 2>  04_style_board.png
    ref_image_2   <Picture 3>  07_loc_henhouse-interior.png

set-10_2-3-4-5-6   (1 scene)
    ref_image_0   <Picture 1>  02_char_der-frosch.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png
    ref_image_2   <Picture 3>  04_style_board.png
    ref_image_3   <Picture 4>  05_char_der-forscher.png
    ref_image_4   <Picture 5>  06_loc_pond.png

set-11_1-4-5-6   (1 scene)
    ref_image_0   <Picture 1>  01_char_federphibium.png
    ref_image_1   <Picture 2>  04_style_board.png
    ref_image_2   <Picture 3>  05_char_der-forscher.png
    ref_image_3   <Picture 4>  06_loc_pond.png

set-12_1-3-4   (1 scene)
    ref_image_0   <Picture 1>  01_char_federphibium.png
    ref_image_1   <Picture 2>  03_char_das-huhn.png
    ref_image_2   <Picture 3>  04_style_board.png


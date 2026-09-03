Drop-in for ComfyUI. Mirrors the path it belongs at, so it is obvious where it
goes: copy (or symlink) watching_hurricanes.py into your own

    <your ComfyUI>/custom_nodes/watching_hurricanes.py

and restart ComfyUI. Stdlib only - no torch, no pip install, no folder wrapper
needed; ComfyUI loads a bare .py in custom_nodes directly.

A symlink is the better move while the kit is changing:

    ln -s "$PWD/comfyui/custom_nodes/watching_hurricanes.py" \
          /path/to/ComfyUI/custom_nodes/watching_hurricanes.py

TWO FILES, both independent - install either or both.

watching_hurricanes.py - the storyboard side. One node under the
"Watching Hurricanes" category:

  Hurricane Song Folder   point it at songs/<name> and it batches the whole song:
                          the prompt, the audio slice, the frame count and the
                          save prefix for one scene per queue run

watching_hurricanes_upscale.py - the pass afterwards. One node:

  Hurricane Clip Folder   walks a folder of rendered clips, one per queue run

It shares no code with the other file and there is no H3 in it. Kept separate so
the upscale pass can be installed, changed or thrown away on its own.

Point it at one of songs/<name>/set-*/, not at the song folder itself: each of
those is a song folder whose scenes all need the same reference sheets, which is
what lets a graph carry only those sheets. The song's __READ_ME.txt holds the
work list of sets.

Paths come out of these nodes as strings, because turning an image or an audio
file into ComfyUI's own types needs torch and this file deliberately has no
dependencies. Wire audio_path into a Load Audio (Path).

Which nodes to pick for the rest, and what your ComfyUI actually has installed:

    ./mvkit probe                       ask the running server
    ./mvkit probe --song <name>          and write a starting workflow into that
                                        song's folder

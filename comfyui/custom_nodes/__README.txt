Drop-in for ComfyUI. Mirrors the path it belongs at, so it is obvious where it
goes: copy (or symlink) watching_hurricanes.py into your own

    <your ComfyUI>/custom_nodes/watching_hurricanes.py

and restart ComfyUI. Stdlib only - no torch, no pip install, no folder wrapper
needed; ComfyUI loads a bare .py in custom_nodes directly.

A symlink is the better move while the kit is changing:

    ln -s "$PWD/comfyui/custom_nodes/watching_hurricanes.py" \
          /path/to/ComfyUI/custom_nodes/watching_hurricanes.py

TWO FILES, both independent - install either or both.

watching_hurricanes.py - the storyboard side. Five nodes under the
"Watching Hurricanes" category:

  Hurricane Song Folder          point it at songs/<name> and it batches the whole song
  Hurricane Storyboard Scene     the same from ALL_scenes.txt, block by block
  Hurricane Reference Inventory   the live <Picture n>/<Video n>/<Audio n> tags
  Hurricane Prompt Builder       assembles the six sections, optionally via a local LLM

watching_hurricanes_upscale.py - the pass afterwards. One node:

  Hurricane Clip Folder   walks a folder of rendered clips, one per queue run

It shares no code with the other file and there is no H3 in it. Kept separate so
the upscale pass can be installed, changed or thrown away on its own.

Only Hurricane Song Folder is needed for the normal job. The other three exist for
building a prompt inside the graph instead of taking the finished one off disk.

Paths come out of these nodes as strings, because turning an image or an audio
file into ComfyUI's own types needs torch and this file deliberately has no
dependencies. Wire audio_path into a Load Audio (Path) and ref_1..ref_9 into
image loaders that accept a path.

Which nodes to pick for the rest, and what your ComfyUI actually has installed:

    ./mvkit probe                       ask the running server
    ./mvkit probe --song <name>          and write a starting workflow into that
                                        song's folder

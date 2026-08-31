Drop-in for ComfyUI. Mirrors the path it belongs at, so it is obvious where it
goes: copy (or symlink) mv_h3_nodes.py into your own

    <your ComfyUI>/custom_nodes/mv_h3_nodes.py

and restart ComfyUI. Stdlib only - no torch, no pip install, no folder wrapper
needed; ComfyUI loads a bare .py in custom_nodes directly.

A symlink is the better move while the kit is changing:

    ln -s "$PWD/comfyui/custom_nodes/mv_h3_nodes.py" \
          /path/to/ComfyUI/custom_nodes/mv_h3_nodes.py

Four nodes appear under the "MusicVideoKit" category:

  MV Song Folder          point it at songs/<name> and it batches the whole song
  MV Storyboard Scene     the same from ALL_scenes.txt, block by block
  MV Reference Inventory   the live <Picture n>/<Video n>/<Audio n> tags
  MV Prompt Builder       assembles the six sections, optionally via a local LLM

Only MV Song Folder is needed for the normal job. The other three exist for
building a prompt inside the graph instead of taking the finished one off disk.

Paths come out of these nodes as strings, because turning an image or an audio
file into ComfyUI's own types needs torch and this file deliberately has no
dependencies. Wire audio_path into a Load Audio (Path) and ref_1..ref_9 into
image loaders that accept a path.

Which nodes to pick for the rest, and what your ComfyUI actually has installed:

    ./mvkit probe                       ask the running server
    ./mvkit probe --song <name>          and write a starting workflow into that
                                        song's folder

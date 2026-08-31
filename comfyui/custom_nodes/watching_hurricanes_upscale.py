"""The upscale pass for a Watching Hurricanes song folder. Separate on purpose.

Copy into ComfyUI/custom_nodes/ next to watching_hurricanes.py, or on its own -
it shares no code with that file and neither needs the other. Stdlib only.

  HurricaneClipFolder   walks a folder of rendered clips, one per queue run

There is no H3 here and no generation of any kind. This is the step after the
renders exist and after you have thrown out the takes you do not want. It also
does no scaling arithmetic: the graph runs one 4x model and writes whatever comes
out. Landing exactly on 4K is a job for the edit, not for this.
"""

import os

CATEGORY = "Watching Hurricanes"
VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv", ".avi")


def list_clips(folder, extensions=""):
    """-> sorted [(path, stem)] so the queue walks the folder in a fixed order.

    Sorted by name, which is why the render prefix names clips after their
    prompt: NN_slug-vN sorts into scene order on its own.
    """
    if not folder or not folder.strip():
        raise ValueError("source_dir is empty - point it at the folder holding "
                         "the rendered clips")
    folder = os.path.expanduser(folder.strip())
    if not os.path.isdir(folder):
        raise FileNotFoundError("source_dir is not a folder: %r" % folder)
    exts = tuple("." + e.strip().lstrip(".").lower()
                 for e in extensions.split(",") if e.strip()) or VIDEO_EXT
    out = []
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(exts) and not f.startswith("."):
            out.append((os.path.join(folder, f), os.path.splitext(f)[0]))
    if not out:
        raise FileNotFoundError(
            "no %s files in %s - check `extensions`, and that this is the folder "
            "the renders actually landed in" % ("/".join(exts), folder))
    return out


class HurricaneClipFolder:
    """Walks a folder of rendered clips, one per queue run.

    Point source_dir at the folder you pruned by hand, set clip_index to
    `increment` and the queue's batch count to clip_count. It lists what is
    ACTUALLY there, so a take you deleted is simply not in the run.

    out_prefix keeps each clip's own name, so an upscaled file stays paired with
    the prompt that made it. ComfyUI will not write outside its own output
    folder, so out_subfolder is a path INSIDE ComfyUI/output - that is its path
    sanitising, not a choice made here.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("video_path", "out_prefix", "clip_count", "name")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "source_dir": ("STRING", {"default": "", "multiline": False}),
            "clip_index": ("INT", {"default": 1, "min": 1, "max": 99999,
                                   "control_after_generate": True}),
            "out_subfolder": ("STRING", {"default": "upscaled"}),
            "extensions": ("STRING", {"default": "mp4,mov,webm,mkv"}),
        }}

    @classmethod
    def IS_CHANGED(cls, source_dir, clip_index, out_subfolder, extensions):
        try:
            m = os.path.getmtime(os.path.expanduser(source_dir.strip()))
        except (OSError, AttributeError):
            m = "missing"
        return "%s:%s:%s:%s:%s" % (source_dir, m, clip_index, out_subfolder,
                                   extensions)

    def run(self, source_dir, clip_index, out_subfolder, extensions):
        clips = list_clips(source_dir, extensions)
        # deliberately NOT clamped: an unattended run with the batch count set too
        # high would otherwise re-render the last clip over and over all night
        if int(clip_index) > len(clips):
            raise ValueError(
                "clip_index %d but the folder holds %d clip(s). Set the queue's "
                "batch count to clip_count (%d), not higher."
                % (int(clip_index), len(clips), len(clips)))
        path, stem = clips[max(int(clip_index), 1) - 1]
        sub = out_subfolder.strip().strip("/")
        return (path, "%s/%s" % (sub, stem) if sub else stem, len(clips), stem)


NODE_CLASS_MAPPINGS = {"HurricaneClipFolder": HurricaneClipFolder}
NODE_DISPLAY_NAME_MAPPINGS = {
    "HurricaneClipFolder": "Hurricane Clip Folder (upscale pass)",
}

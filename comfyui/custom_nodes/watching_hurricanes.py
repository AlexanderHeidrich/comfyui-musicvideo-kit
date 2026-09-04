"""One node: turn a MusicVideoKit song folder into a batch of H3 renders.

Copy into ComfyUI/custom_nodes/ and restart. Stdlib only - no torch, no numpy,
nothing to install.

  HurricaneSongFolder   point it at songs/<name>, set scene_index to `increment`
                        and the queue's batch count to scene_count, press Run once

It hands out the three things that change from scene to scene and nothing else.
The reference sheets are NOT among them: within one set folder they are the same
for every scene, so the LoadImage nodes that already point at them are correct.

There is no audio here. H3 is given no audio reference at all: reference audio is
a timbre anchor, not playback, and handing it a slice carrying the same words as
the prompt is what produced clips that sang the wrong lyrics. The song is laid
under the picture in the edit instead.

The upscale pass lives in watching_hurricanes_upscale.py, separately.
"""

import json
import os
import re

CATEGORY = "Watching Hurricanes"


def read_song_folder(song):
    """-> [{scene, title, frames, prompts}] from __SCENES.tsv.

    That file is the authority on pairing: it already says which prompt files and
    which slice belong to each scene, so nothing here re-derives it.
    """
    song = os.path.expanduser((song or "").strip())
    if not song:
        raise ValueError("song_path is empty - point it at a built song folder, "
                         "the one holding the NN_*.txt files")
    man = os.path.join(song, "__SCENES.tsv")
    if not os.path.isfile(man):
        raise FileNotFoundError(
            "%s has no __SCENES.tsv - point song_path at a built song folder "
            "(the one holding NN_*.txt), not at _source or the repo root." % song)
    with open(man, encoding="utf-8") as fh:
        rows = [l.rstrip("\n").split("\t") for l in fh if l.strip()]
    head, rows = rows[0], rows[1:]
    out = []
    for r in rows:
        d = dict(zip(head, r))
        pf = [f for f in (d.get("prompts") or "").split() if f.endswith(".txt")]
        out.append({
            "scene": d.get("scene", "?"),
            "title": re.sub(r"^\d+_|-v\d+\.txt$", "", pf[0]).replace("-", " ")
                     if pf else "",
            "frames": int(d.get("frames") or 0),
            "prompts": {f.rsplit("-", 1)[-1][:-4]: os.path.join(song, f)
                        for f in pf},
        })
    if not out:
        raise ValueError("__SCENES.tsv lists no scenes")
    return out


class HurricaneSongFolder:
    """A song folder, one scene per queue run.

    scene_index on `increment` + batch count = scene_count renders the whole song
    in one press of Run. An index past the end is an error rather than a clamp: a
    batch count set too high would otherwise re-render the last scene for as long
    as the queue lasts.

    frames is always 243 (10.125 s) as the kit builds it, but it is read from the
    file rather than assumed, so a hand-edited row still works.
    """

    CATEGORY = CATEGORY
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("prompt", "frames", "scene_count", "save_prefix")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "song_path": ("STRING", {"default": "", "multiline": False}),
            "scene_index": ("INT", {"default": 1, "min": 1, "max": 9999,
                                    "control_after_generate": True}),
            "variant": (["v1", "v2", "v3"], {"default": "v1"}),
            "out_subfolder": ("STRING", {"default": "", "multiline": False}),
        }}

    @classmethod
    def IS_CHANGED(cls, song_path, scene_index, variant, out_subfolder=""):
        try:
            m = os.path.getmtime(os.path.join(os.path.expanduser(song_path.strip()),
                                              "__SCENES.tsv"))
        except (OSError, AttributeError):
            m = "missing"
        return "%s:%s:%s:%s:%s" % (song_path, m, scene_index, variant,
                                   out_subfolder)

    def run(self, song_path, scene_index, variant, out_subfolder=""):
        scenes = read_song_folder(song_path)
        if int(scene_index) > len(scenes):
            raise ValueError(
                "scene_index %d but this song has %d scene(s). Set the queue's "
                "batch count to scene_count (%d), not higher."
                % (int(scene_index), len(scenes), len(scenes)))
        sc = scenes[max(int(scene_index), 1) - 1]

        pf = sc["prompts"].get(variant)
        if not pf:
            have = ", ".join(sorted(sc["prompts"])) or "none"
            raise ValueError("scene %s has no %s variant (it has: %s)"
                             % (sc["scene"], variant, have))
        with open(pf, encoding="utf-8") as fh:
            prompt = fh.read()

        base = (out_subfolder.strip().strip("/") or
                os.path.basename(os.path.abspath(os.path.expanduser(
                    song_path.strip()))))
        prefix = "%s/%s" % (base, os.path.basename(pf)[:-4])
        return (prompt, sc["frames"], len(scenes), prefix)


NODE_CLASS_MAPPINGS = {"HurricaneSongFolder": HurricaneSongFolder}
NODE_DISPLAY_NAME_MAPPINGS = {"HurricaneSongFolder": "Hurricane Song Folder"}

class MVSongFolder(HurricaneSongFolder):
    """The class was briefly called this. A graph saved against the old name still
    loads; DEPRECATED keeps it out of the node menu, so the only thing you find
    under "Watching Hurricanes" is the one node that is current."""

    DEPRECATED = True


NODE_CLASS_MAPPINGS["MVSongFolder"] = MVSongFolder

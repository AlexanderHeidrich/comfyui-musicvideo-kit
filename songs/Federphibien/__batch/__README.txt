Index files for batching this folder through ComfyUI.
Each pair is line-for-line aligned: line N of -prompts.txt is the
prompt for line N of -audio.txt. One pair per frame count, so you
set `length` once per group.

group                  length   queue batch count
f124-v1                124      36
f124-v2                124      36
f124-v3                124      36
f141-v1                141      4
f141-v2                141      4
f141-v3                141      4
f158-v1                158      4
f158-v2                158      4
f158-v3                158      4
f226-v1                226      1
f226-v2                226      1
f226-v3                226      1
f277-v1                277      1
f277-v2                277      1
f277-v3                277      1
f294-v1                294      1
f294-v2                294      1
f294-v3                294      1

Wiring, and why core nodes are not enough: see docs/comfyui-batch.md
Paths are relative to the song folder - the one directly above this
one. Prefix them with wherever that folder lives on the machine that
runs ComfyUI.

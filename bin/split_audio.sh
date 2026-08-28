#!/usr/bin/env bash
# Cut the song at the scene boundaries in scenes.tsv.
#
#   bin/split_audio.sh <audio> <scenes.tsv> [outdir]
#
# Writes scene_NN.mp3; build_storyboards.py then renames each one after its
# prompt file so the pair sits side by side.
#
# Re-encodes rather than stream-copying: -c copy lands on the nearest MP3 frame
# and would drift by tens of ms per cut, which defeats the point of snapping the
# scenes to H3's frame grid in the first place.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_lib.sh"

AUDIO="${1:?usage: split_audio.sh <audio> <scenes.tsv> [outdir]}"
SCENES="${2:?}"; OUT="${3:-$(dirname "$SCENES")/..}"
[ -f "$AUDIO" ] || { echo "not found: $AUDIO"; exit 1; }
[ -f "$SCENES" ] || { echo "not found: $SCENES"; exit 1; }
need_ffmpeg
mkdir -p "$OUT"
n=0
# tr strips CR so a scenes.tsv saved on Windows still parses.
# ffmpeg needs -nostdin or it drains the loop's stdin and eats the next scenes.
while IFS=$'\t' read -r scene start end frames dur drift rest; do
  [ "$scene" = "scene" ] && continue
  [ -z "${scene:-}" ] && continue
  f=$(printf "%s/scene_%02d.mp3" "$OUT" "$scene")
  "$FFMPEG" -nostdin -v error -y -ss "$start" -t "$dur" -i "$AUDIO" -map 0:a -c:a libmp3lame -q:a 2 "$f"
  got=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$f")
  printf "  scene %02d  %8.3f +%7.4f  ->  %-22s got %.4f s\n" \
    "$scene" "$start" "$dur" "$(basename "$f")" "${got:-0}"
  n=$((n+1))
done < <(tr -d '\r' < "$SCENES")
echo "wrote $n slices to $OUT/"

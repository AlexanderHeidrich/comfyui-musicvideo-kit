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
need_ffmpeg; need_python
TOTAL=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$AUDIO")
mkdir -p "$OUT"
n=0
# tr strips CR so a scenes.tsv saved on Windows still parses.
# ffmpeg needs -nostdin or it drains the loop's stdin and eats the next scenes.
while IFS=$'\t' read -r scene start end frames dur drift rest; do
  [ "$scene" = "scene" ] && continue
  [ -z "${scene:-}" ] && continue
  f=$(printf "%s/scene_%02d.mp3" "$OUT" "$scene")
  # A scene with no window of the song - the Vorspann, the compositing elements -
  # gets a slice of SILENCE of exactly the right length, not no slice at all. An
  # empty audio path is what an audio loader chokes on, and it took down the first
  # job of a batch run; silence matches what those prompts already say ("there is
  # no music in this clip") and keeps every scene renderable by the same graph.
  if [ "$start" = "-" ]; then
    "$FFMPEG" -nostdin -v error -y -f lavfi -i anullsrc=r=44100:cl=stereo \
      -t "$dur" -c:a libmp3lame -q:a 9 "$f"
    got=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$f")
    printf "  scene %02d  %8s +%7.4f  ->  %-22s got %.4f s  (silence - no window of the song)\n" \
      "$scene" "-" "$dur" "$(basename "$f")" "${got:-0}"
    n=$((n+1))
    continue
  fi
  # apad + an output -t so the slice is ALWAYS exactly `dur` long. A scene that
  # runs past the end of the song would otherwise hand H3 an audio reference
  # shorter than the clip it is meant to drive.
  "$FFMPEG" -nostdin -v error -y -ss "$start" -i "$AUDIO" -map 0:a -af apad \
    -t "$dur" -c:a libmp3lame -q:a 2 "$f"
  got=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$f")
  pad=""
  if [ -n "${TOTAL:-}" ]; then
    over=$("$PY" -c "print('%.3f' % max(0.0, ($start + $dur) - $TOTAL))" 2>/dev/null || echo 0)
    case "$over" in 0|0.000) ;; *) pad="  (padded ${over}s of silence - past the end of the song)" ;; esac
  fi
  printf "  scene %02d  %8.3f +%7.4f  ->  %-22s got %.4f s%s\n" \
    "$scene" "$start" "$dur" "$(basename "$f")" "${got:-0}" "$pad"
  n=$((n+1))
done < <(tr -d '\r' < "$SCENES")
echo "wrote $n slices to $OUT/"

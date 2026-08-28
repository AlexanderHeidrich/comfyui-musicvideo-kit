#!/usr/bin/env bash
# Join rendered scene clips into one video, in filename order.
#   bin/concat.sh <dir-with-mp4s> [out.mp4]
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
DIR="${1:?usage: concat.sh <dir-with-mp4s> [out.mp4]}"
[ -d "$DIR" ] || { echo "not a directory: $DIR"; exit 1; }
need_ffmpeg
DIR="$(cd "$DIR" && pwd)"
OUT="${2:-$DIR/../assembled.mp4}"
case "$OUT" in /*|?:[/\\]*) ;; *) OUT="$PWD/$OUT" ;; esac   # resolve before cd

cd "$DIR"
: > .concat.txt
found=0
for f in *.mp4; do
  [ -e "$f" ] || continue
  printf "file '%s'\n" "$f" >> .concat.txt
  found=$((found+1))
done
[ "$found" -gt 0 ] || { rm -f .concat.txt; echo "no .mp4 files in $DIR"; exit 1; }
LC_ALL=C sort -o .concat.txt .concat.txt

"$FFMPEG" -nostdin -v error -stats -f concat -safe 0 -i .concat.txt -c copy "$OUT"
rm -f .concat.txt
echo "wrote $OUT  ($found clips)"
"$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$OUT" | xargs echo "duration:"

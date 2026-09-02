#!/usr/bin/env bash
# Scaffold a song folder with every input slot the pipeline reads.
#   bin/new_song.sh <name> <audio-file> [style|other-song]
set -euo pipefail
NAME="${1:?usage: new_song.sh <name> <audio-file> [style|other-song]}"
AUDIO="${2:?usage: new_song.sh <name> <audio-file> [style|other-song]}"
PICK="${3:-_TEMPLATE}"
KIT="$(cd "$(dirname "$0")/.." && pwd)"
DST="$KIT/songs/$NAME"; SRC="$DST/_source"
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
[ -f "$AUDIO" ] || { echo "not found: $AUDIO"; exit 1; }

EXT="${AUDIO##*.}"; case "$EXT" in "$AUDIO"|*/*) EXT=mp3 ;; esac
mkdir -p "$SRC/refs"
cp "$AUDIO" "$SRC/song.$EXT"

# blocks come from another song if you name one, otherwise from templates/
if [ -f "$KIT/songs/$PICK/_source/brief.txt" ]; then
  FROM="song '$PICK'"
  cp "$KIT/songs/$PICK/_source/brief.txt" "$SRC/brief.txt"
  [ -f "$KIT/songs/$PICK/_source/tail.txt" ] && cp "$KIT/songs/$PICK/_source/tail.txt" "$SRC/tail.txt"
elif [ -f "$KIT/templates/styles/$PICK.txt" ]; then
  FROM="templates (style: $PICK)"
  # the style library stays in the kit: it is long-form raw material, and what
  # the song needs is the ~900-character [style] block distilled out of it
  { printf '# Style starting point: templates/styles/%s.txt\n' "$PICK"
    printf '# Read that file and distil it into the [style] block below. Do not\n'
    printf '# paste it whole - every prompt carries this block.\n\n'
    cat "$KIT/templates/brief.txt"; } > "$SRC/brief.txt"
  cp "$KIT/templates/tail/default.txt" "$SRC/tail.txt"
else
  echo "no style '$PICK'. Available:"
  ls "$KIT/templates/styles" | sed 's/\.txt$//;s/^/  /'
  ls -d "$KIT"/songs/*/ 2>/dev/null | sed 's#.*/songs/##;s#/$##;s/^/  /'
  rm -rf "$DST"; exit 1
fi

echo '{}' > "$SRC/content.json"
cat > "$SRC/lyrics.txt" <<'EOF'
# The real lyrics, one line per sung line. The ASR transcript is wrong on sung
# material and is only used for timing - this file is what reaches the model.
# Prefix a line with [mm:ss] and it is placed on the scene covering that time:
#   [00:18] Ich sitze traurig am Rand vom Teich
# Without timestamps the lyric is taken from the screenplay's quoted lines.
EOF
cat > "$SRC/style_examples.txt" <<'EOF'
# Free notes on the look: shows, films, illustrators, eras, "like X but rougher".
# Read by the drafting pass and DISTILLED into brief.txt's [style] - not pasted
# the prompt, because brand and show names do not reproduce reliably. Concrete
# craft descriptions do.
EOF
cat > "$SRC/refs/__README.txt" <<'EOF'
Reference images and clips. The filename decides what the reference IS and in
which order H3 loads it, so stick to the schema:

  [NN_]char_<slug>.png     a character           -> <Picture n>
  [NN_]style_<slug>.png    a look / colour board -> <Picture n>
  [NN_]loc_<slug>.png      a location or set     -> <Picture n>
  [NN_]prop_<slug>.png     a prop                -> <Picture n>
  [NN_]video_<slug>.mp4    a motion reference    -> <Video n>

NN is optional and only sets load order (01_ first). Limits: 9 images,
3 videos, 12 media in total, and at least one image or video - H3 rejects
audio-only input. Run `mvkit refs <song>` to see the tags it will actually get.
EOF

cat <<MSG
scaffolded $DST  (blocks from $FROM)

  _source/song.$EXT
  _source/refs/            drop reference images here, see refs/__README.txt
  _source/brief.txt        [style], [sound], [music] and one [subject] per
                           reference - the ONLY thing the prompts are built from
  _source/style_examples.txt   free notes on the look, distilled into [style]
  _source/tail.txt         audio fallback, used only where brief.txt is silent
  _source/lyrics.txt       the real lyrics
  _source/content.json     empty - filled by \`mvkit draft\`

optional but better: put the screenplay in _source/ as a pdf (any name), or
write _source/drehbuch.txt yourself. It drives the scene split.

next:
  ./mvkit all $NAME
MSG

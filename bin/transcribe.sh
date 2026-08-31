#!/usr/bin/env bash
# Transcribe a song into ONE metadata file the storyboard generator consumes.
#
#   bin/transcribe.sh <audio-file> [outdir]
#
# Writes  <outdir>/transcript.json   full metadata (segments, words, silences)
#         <outdir>/transcript.tsv    start  end  text
#         <outdir>/transcript.txt    human readable
#
# Whisper reliably gives up partway through sung material - the first pass on
# a 143s track stopped at 115s. So this re-transcribes every coverage gap it
# finds and reports what it could not fill.
#
# env: WHISPER_MODEL_NAME (default ggml-large-v3-turbo.bin), WHISPER_LANG (de),
#      WHISPER_MODEL_DIR, WHISPER_BIN, FFMPEG, FFPROBE, PY
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_lib.sh"

AUDIO="${1:?usage: transcribe.sh <audio-file> [outdir]}"
OUT="${2:-.}"
LANG_="${WHISPER_LANG:-de}"
MODEL_NAME="${WHISPER_MODEL_NAME:-ggml-large-v3-turbo.bin}"
MODEL="$(model_dir)/$MODEL_NAME"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/mvkit.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

[ -f "$AUDIO" ] || { echo "not found: $AUDIO"; exit 1; }
mkdir -p "$OUT"
need_ffmpeg; need_python; need_whisper

if [ ! -f "$MODEL" ]; then
  mkdir -p "$(dirname "$MODEL")"
  echo ">> downloading $MODEL_NAME once -> $MODEL"
  URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$MODEL_NAME"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail --progress-bar "$URL" -o "$MODEL.part"
  elif command -v wget >/dev/null 2>&1; then
    wget -q --show-progress -O "$MODEL.part" "$URL"
  else
    echo "need curl or wget to fetch the model"; exit 1
  fi
  mv "$MODEL.part" "$MODEL"
fi

DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$AUDIO")
echo ">> $(basename "$AUDIO")  ${DUR}s  model=$MODEL_NAME lang=$LANG_"

run() {  # run <start> <dur|0> <prefix> [extra flags...]
  local ss="$1" t="$2" pre="$3"; shift 3
  if [ "$t" = "0" ]; then
    "$FFMPEG" -nostdin -v error -y -ss "$ss" -i "$AUDIO" -ar 16000 -ac 1 -c:a pcm_s16le "$WORK/$pre.wav"
  else
    "$FFMPEG" -nostdin -v error -y -ss "$ss" -t "$t" -i "$AUDIO" -ar 16000 -ac 1 -c:a pcm_s16le "$WORK/$pre.wav"
  fi
  "$WHISPER_BIN" -m "$MODEL" -f "$WORK/$pre.wav" -l "$LANG_" -oj -of "$WORK/$pre" "$@" >/dev/null 2>&1 || true
}

echo ">> pass 1: full file"
run 0 0 seg
echo ">> pass 2: word level"
run 0 0 word -ml 1

# gap filling: ask python where coverage is missing, transcribe those windows
for round in 1 2 3; do
  GAPS=$($PY - "$WORK" "$DUR" <<'PY'
import glob, json, os, sys
work, dur = sys.argv[1], float(sys.argv[2])
segs=[]
for p in glob.glob(os.path.join(work,"seg*.json")):
    off = 0.0
    b = os.path.basename(p)[:-5]
    if b.startswith("seggap_"): off = float(b.split("_")[1])
    try: d=json.load(open(p,encoding="utf-8"))
    except Exception: continue
    for s in d.get("transcription",[]):
        if (s.get("text") or "").strip():
            segs.append((off+s["offsets"]["from"]/1000.0, off+s["offsets"]["to"]/1000.0))
segs.sort()
gaps=[]; cur=0.0
for a,b in segs:
    if a-cur > 4.0: gaps.append((cur,a))
    cur=max(cur,b)
if dur-cur > 4.0: gaps.append((cur,dur))
print(" ".join("%.2f:%.2f"%(max(0,a-1.5),min(dur,b+1.5)) for a,b in gaps))
PY
)
  [ -z "$GAPS" ] && { echo ">> coverage complete"; break; }
  echo ">> round $round: filling gaps -> $GAPS"
  for g in $GAPS; do
    a="${g%%:*}"; b="${g##*:}"
    len=$($PY -c "print(round(float('$b')-float('$a'),2))")
    run "$a" "$len" "seggap_${a}"
    run "$a" "$len" "wordgap_${a}" -ml 1
  done
done

echo ">> silences"
"$FFMPEG" -nostdin -v info -i "$WORK/seg.wav" -af silencedetect=noise=-30dB:d=0.25 -f null - 2>"$WORK/sil.log" || true

$PY - "$AUDIO" "$DUR" "$MODEL_NAME" "$LANG_" "$WORK" "$OUT" <<'PY'
import glob, json, os, re, sys
audio,dur,model,lang,work,out = sys.argv[1],float(sys.argv[2]),sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6]

def collect(kind):
    rows=[]
    for p in sorted(glob.glob(os.path.join(work,kind+"*.json"))):
        base=os.path.basename(p)[:-5]
        off=float(base.split("_")[1]) if "gap_" in base else 0.0
        try: d=json.load(open(p,encoding="utf-8"))
        except Exception: continue
        for s in d.get("transcription",[]):
            t=(s.get("text") or "").strip()
            if not t: continue
            rows.append({"start":round(off+s["offsets"]["from"]/1000.0,3),
                         "end":round(off+s["offsets"]["to"]/1000.0,3),"text":t})
    rows.sort(key=lambda r:(r["start"],r["end"]))
    keep=[]
    for r in rows:  # drop overlapping duplicates from gap windows
        if keep and r["start"] < keep[-1]["end"]-0.25 and r["text"]==keep[-1]["text"]: continue
        if keep and abs(r["start"]-keep[-1]["start"])<0.25 and r["text"]==keep[-1]["text"]: continue
        keep.append(r)
    return keep

segments, words = collect("seg"), collect("word")

sil=[];cur=None
for line in open(os.path.join(work,"sil.log"),encoding="utf-8",errors="ignore"):
    a=re.search(r"silence_start:\s*([\d.]+)",line); b=re.search(r"silence_end:\s*([\d.]+)",line)
    if a: cur=float(a.group(1))
    if b and cur is not None: sil.append({"start":round(cur,3),"end":round(float(b.group(1)),3)}); cur=None
if cur is not None: sil.append({"start":round(cur,3),"end":round(dur,3)})   # silence to EOF

# whisper fills trailing silence with a hallucinated line repeated to the end of
# the file. Nothing after the last real audio can be a transcript of anything.
audio_end=dur
if sil and sil[-1]["end"]>=dur-0.30 and sil[-1]["start"]<dur-0.30:
    audio_end=sil[-1]["start"]
cut=[s for s in segments if s["start"]>=audio_end-0.25 or s["start"]>dur]
if cut:
    segments=[s for s in segments if s not in cut]
    words=[w for w in words if w["start"]<audio_end-0.25 and w["start"]<=dur]
    print("trailing silence: dropped %d segment(s) after %.2fs (hallucinated)"
          %(len(cut),audio_end))

covered=0.0; holes=[]; c=0.0
for s in segments:
    if s["start"]-c>2.0: holes.append({"start":round(c,2),"end":round(s["start"],2)})
    c=max(c,s["end"])
if dur-c>2.0: holes.append({"start":round(c,2),"end":round(dur,2)})
for s in segments: covered+=max(0.0,s["end"]-s["start"])

meta={"source":os.path.basename(audio),"duration":round(dur,3),"language":lang,"model":model,
      "segment_count":len(segments),"word_count":len(words),
      "coverage_pct":round(100.0*min(covered,dur)/dur,1),"uncovered":holes,
      "segments":segments,"words":words,"silences":sil}
json.dump(meta,open(os.path.join(out,"transcript.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
with open(os.path.join(out,"transcript.tsv"),"w",encoding="utf-8",newline="\n") as fh:
    fh.write("start\tend\ttext\n")
    for s in segments: fh.write("%.3f\t%.3f\t%s\n"%(s["start"],s["end"],s["text"]))
with open(os.path.join(out,"transcript.txt"),"w",encoding="utf-8",newline="\n") as fh:
    for s in segments: fh.write("[%07.3f -> %07.3f] %s\n"%(s["start"],s["end"],s["text"]))
print()
print("duration   : %.2fs (%d:%05.2f)"%(dur,int(dur)//60,dur%60))
print("segments   : %d   words: %d   silences: %d"%(len(segments),len(words),len(sil)))
print("coverage   : %.1f%%"%meta["coverage_pct"])
print("uncovered  : %s"%(holes or "none"))
print()
for s in segments: print("  [%06.2f -> %06.2f] %s"%(s["start"],s["end"],s["text"]))
PY
echo
echo "wrote $OUT/transcript.json  transcript.tsv  transcript.txt"

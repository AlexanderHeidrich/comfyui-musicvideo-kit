# Shared lookups for the shell steps. Sourced, not executed.
# Every tool is overridable by env so Docker, Homebrew, Git Bash and WSL all fit.

case "$(uname -s 2>/dev/null)" in
  Darwin) MVKIT_OS=mac ;;
  Linux)  MVKIT_OS=linux ;;
  MINGW*|MSYS*|CYGWIN*) MVKIT_OS=windows ;;
  *)      MVKIT_OS=unknown ;;
esac

_first() {                 # _first VAR name...  -> first name on PATH
  local v="$1" c; shift
  eval "local pre=\${$v:-}"
  if [ -n "$pre" ]; then command -v "$pre" >/dev/null 2>&1 && { eval "$v=\$pre"; return 0; }; fi
  for c in "$@"; do command -v "$c" >/dev/null 2>&1 && { eval "$v=\$c"; return 0; }; done
  return 1
}

_hint() {                  # per-platform install line
  case "$MVKIT_OS" in
    mac)     echo "  brew install $1" ;;
    linux)   echo "  apt-get install -y $1   (or your package manager)" ;;
    windows) echo "  use Docker: mvkit.cmd <command>   (or install $1 in WSL/Git Bash)" ;;
    *)       echo "  install $1" ;;
  esac
}

need_ffmpeg() {
  _first FFMPEG ffmpeg && _first FFPROBE ffprobe && return 0
  echo "ffmpeg/ffprobe not found."; _hint ffmpeg; exit 1
}

need_python() {
  _first PY python3 python && return 0
  if command -v py >/dev/null 2>&1; then PY="py -3"; return 0; fi
  echo "python 3 not found."; _hint python3; exit 1
}

need_whisper() {
  # upstream renamed main -> whisper-cli; distro packages still ship either
  _first WHISPER_BIN whisper-cli whisper-cpp whisper main && return 0
  echo "whisper-cli not found."
  case "$MVKIT_OS" in
    mac)     echo "  brew install whisper-cpp" ;;
    linux)   echo "  build https://github.com/ggml-org/whisper.cpp, or run via Docker" ;;
    windows) echo "  mvkit.cmd transcribe ...   (runs it in Docker)" ;;
  esac
  echo "  or set WHISPER_BIN=/path/to/whisper-cli"
  exit 1
}

model_dir() { echo "${WHISPER_MODEL_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/whisper}"; }

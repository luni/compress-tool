#!/usr/bin/env bash
set -euo pipefail

ARCHIVE=""
OUTPUT=""
QUIET=0
FORCE=0
KEEP_WORKDIR=0
REMOVE_SOURCE=0
TEMP_PARENT=""
SHA256_FILE=""
SHA256_ENABLED=0
SHA256_APPEND=0
ZEEKSTD_BIN_FROM_FLAG=0
ZEEKSTD_BIN="${ZEEKSTD_BIN:-${HOME}/.cargo/bin/zeekstd}"
ARCHIVE_TYPE=""
INPUT_STREAM_DESC=""
declare -a ZEEKSTD_ARGS
declare -a INPUT_STREAM_CMD=()
ZEEKSTD_ARGS=(--force --compression-level 10)

usage() {
  cat <<'EOF'
Usage:
  convert-to-tarzst.sh [options] ARCHIVE

Description:
  - For *.7z inputs: extracts the archive into a temporary directory, repacks
    its contents into an uncompressed tar stream, and compresses that stream
    with zeekstd to produce a seekable .tar.zst file.
  - For *.tar.gz/*.tgz, *.tar.xz/*.txz, or *.tar.bz2/*.tbz* inputs: streams the
    tarball through the appropriate decompressor directly into zeekstd without
    creating a temporary workspace.

Options:
  -o, --output FILE       Target .tar.zst path (default: ARCHIVE basename + .tar.zst)
      --zeekstd PATH      Override zeekstd binary (default: ${HOME}/.cargo/bin/zeekstd)
      --zeekstd-arg ARG   Additional argument to pass to zeekstd (repeatable)
      --temp-dir DIR      Create the temporary extraction directory under DIR
                           (only applies to .7z inputs)
      --sha256            Emit SHA-256 manifest (only for .7z inputs; defaults
                           to ARCHIVE basename + .sha256)
      --sha256-file FILE  Emit SHA-256 manifest to FILE
      --sha256-append     Append to the SHA-256 file instead of truncating
  -f, --force             Overwrite the output file if it already exists
      --remove-source     Delete the original .7z archive after a successful conversion
  -q, --quiet             Suppress progress logs
  -k, --keep-temp         Keep the temporary extraction directory (printed on success;
                           only useful for .7z inputs)
  -h, --help              Show this help message
EOF
}

log() {
  [[ "$QUIET" -eq 1 ]] && return 0
  printf '%s\n' "$*" >&2
}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 2
}

default_basename_path() {
  local archive="$1" dir base
  dir="$(dirname -- "$archive")"
  base="$(basename -- "$archive")"
  local lowered="${base,,}"
  case "$lowered" in
    *.tar.gz|*.tar.xz|*.tar.bz2)
      base="${base%.*}"
      base="${base%.*}"
      ;;
    *.tgz|*.txz|*.tbz|*.tbz2)
      base="${base%.*}"
      ;;
    *.7z)
      base="${base%.*}"
      ;;
  esac
  printf '%s/%s\n' "$dir" "$base"
}

default_sha256_path() {
  local archive="$1"
  printf '%s.sha256\n' "$(default_basename_path "$archive")"
}

prepare_sha256_file() {
  local file="$1" append_flag="$2"
  [[ -z "$file" ]] && return 0
  mkdir -p -- "$(dirname -- "$file")" 2>/dev/null || true
  if [[ "$append_flag" -eq 1 ]]; then
    : >>"$file"
  else
    : >"$file"
  fi
}

write_sha256_manifest() {
  local root="$1" dest="$2" file rel hash
  [[ -z "$dest" ]] && return 0

  # Sort paths for deterministic output
  while IFS= read -r -d '' file; do
    rel="${file#$root/}"
    if [[ "$rel" == "$file" ]]; then
      rel="$(basename -- "$file")"
    fi
    hash="$(sha256sum -- "$file" | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$rel" >>"$dest"
  done < <(LC_ALL=C find "$root" -type f -print0 | LC_ALL=C sort -z)
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required tool '$1' is not on PATH."
}

detect_archive_type() {
  local archive="$1" lowered="${archive,,}"
  case "$lowered" in
    *.7z)
      printf '7z'
      ;;
    *.tar.gz|*.tgz)
      printf 'tar.gz'
      ;;
    *.tar.xz|*.txz)
      printf 'tar.xz'
      ;;
    *.tar.bz2|*.tbz|*.tbz2)
      printf 'tar.bz2'
      ;;
    *)
      die "Unsupported archive extension for $archive (supported: .7z, .tar.gz/.tgz, .tar.xz/.txz, .tar.bz2/.tbz/.tbz2)"
      ;;
  esac
}

setup_stream_input() {
  case "$ARCHIVE_TYPE" in
    tar.gz)
      if command -v pigz >/dev/null 2>&1; then
        INPUT_STREAM_CMD=(pigz -dc -- "$ARCHIVE")
        INPUT_STREAM_DESC="pigz -dc"
      else
        require_cmd gzip
        INPUT_STREAM_CMD=(gzip -dc -- "$ARCHIVE")
        INPUT_STREAM_DESC="gzip -dc"
      fi
      ;;
    tar.xz)
      if command -v pixz >/dev/null 2>&1; then
        INPUT_STREAM_CMD=(pixz -dc -- "$ARCHIVE")
        INPUT_STREAM_DESC="pixz -dc"
      else
        require_cmd xz
        INPUT_STREAM_CMD=(xz -dc -- "$ARCHIVE")
        INPUT_STREAM_DESC="xz -dc"
      fi
      ;;
    tar.bz2)
      if command -v pbzip2 >/dev/null 2>&1; then
        INPUT_STREAM_CMD=(pbzip2 -dc -- "$ARCHIVE")
        INPUT_STREAM_DESC="pbzip2 -dc"
      else
        require_cmd bzip2
        INPUT_STREAM_CMD=(bzip2 -dc -- "$ARCHIVE")
        INPUT_STREAM_DESC="bzip2 -dc"
      fi
      ;;
    *)
      die "Streaming conversion is not supported for archive type '$ARCHIVE_TYPE'"
      ;;
  esac
}

WORKDIR=""
TMP_OUTPUT=""
cleanup() {
  if [[ "$KEEP_WORKDIR" -eq 0 && -n "$WORKDIR" && -d "$WORKDIR" ]]; then
    rm -rf -- "$WORKDIR"
  elif [[ -n "$WORKDIR" && -d "$WORKDIR" ]]; then
    log "Temporary directory kept at: $WORKDIR"
  fi
  if [[ -n "$TMP_OUTPUT" && -f "$TMP_OUTPUT" ]]; then
    rm -f -- "$TMP_OUTPUT"
  fi
}
trap cleanup EXIT INT TERM

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      [[ $# -lt 2 ]] && die "Missing value for $1"
      OUTPUT="$2"
      shift 2
      ;;
    --zeekstd)
      [[ $# -lt 2 ]] && die "Missing value for $1"
      ZEEKSTD_BIN="$2"
      ZEEKSTD_BIN_FROM_FLAG=1
      shift 2
      ;;
    --zeekstd-arg)
      [[ $# -lt 2 ]] && die "Missing value for $1"
      ZEEKSTD_ARGS+=("$2")
      shift 2
      ;;
    --temp-dir)
      [[ $# -lt 2 ]] && die "Missing value for $1"
      TEMP_PARENT="$2"
      shift 2
      ;;
    --sha256)
      SHA256_ENABLED=1
      shift
      ;;
    --sha256-file)
      [[ $# -lt 2 ]] && die "Missing value for $1"
      SHA256_ENABLED=1
      SHA256_FILE="$2"
      shift 2
      ;;
    --sha256-append)
      SHA256_APPEND=1
      shift
      ;;
    --remove-source)
      REMOVE_SOURCE=1
      shift
      ;;
    -f|--force)
      FORCE=1
      shift
      ;;
    -q|--quiet)
      QUIET=1
      shift
      ;;
    -k|--keep-temp)
      KEEP_WORKDIR=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "Unknown option: $1"
      ;;
    *)
      if [[ -z "$ARCHIVE" ]]; then
        ARCHIVE="$1"
      else
        die "Only one archive can be converted at a time."
      fi
      shift
      ;;
  esac
done

if [[ $# -gt 0 ]]; then
  die "Unexpected positional arguments: $*"
fi

[[ -n "$ARCHIVE" ]] || die "Archive path is required."
[[ -f "$ARCHIVE" ]] || die "Archive not found: $ARCHIVE"

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="$(default_basename_path "$ARCHIVE").tar.zst"
fi

if [[ -e "$OUTPUT" && "$FORCE" -ne 1 ]]; then
  die "Output already exists: $OUTPUT (use --force to overwrite)"
fi

ARCHIVE_TYPE="$(detect_archive_type "$ARCHIVE")"

if [[ "$SHA256_ENABLED" -eq 1 && "$ARCHIVE_TYPE" != "7z" ]]; then
  die "--sha256 is only supported for .7z inputs."
fi

if [[ "$SHA256_ENABLED" -eq 1 && -z "$SHA256_FILE" ]]; then
  SHA256_FILE="$(default_sha256_path "$ARCHIVE")"
fi

if [[ "$ARCHIVE_TYPE" == "7z" ]]; then
  require_cmd 7z
  require_cmd tar
else
  setup_stream_input
fi

if [[ "$SHA256_ENABLED" -eq 1 ]]; then
  require_cmd sha256sum
  prepare_sha256_file "$SHA256_FILE" "$SHA256_APPEND"
fi

if [[ -n "$TEMP_PARENT" ]]; then
  mkdir -p -- "$TEMP_PARENT" || die "Failed to create temp directory parent: $TEMP_PARENT"
fi

if [[ ! -x "$ZEEKSTD_BIN" ]]; then
  if [[ "$ZEEKSTD_BIN_FROM_FLAG" -eq 0 ]]; then
    if command -v zeekstd >/dev/null 2>&1; then
      ZEEKSTD_BIN="$(command -v zeekstd)"
    else
      die "zeekstd binary not found at ${HOME}/.cargo/bin/zeekstd (run ./install-zeekstd.sh)."
    fi
  else
    die "zeekstd binary is not executable: $ZEEKSTD_BIN"
  fi
fi

if [[ "$ARCHIVE_TYPE" == "7z" ]]; then
  template="convert-to-tarzst.XXXXXX"
  if [[ -n "$TEMP_PARENT" ]]; then
    WORKDIR="$(mktemp -d -p "$TEMP_PARENT" "$template")" || die "Failed to create temporary directory under $TEMP_PARENT"
  else
    WORKDIR="$(mktemp -d)" || die "Failed to create temporary directory"
  fi
  log "Extracting $ARCHIVE into $WORKDIR ..."
  if [[ "$QUIET" -eq 1 ]]; then
    7z x -y -bso0 -bsp0 -o"$WORKDIR" -- "$ARCHIVE" >/dev/null
  else
    7z x -y -bso0 -bsp1 -o"$WORKDIR" -- "$ARCHIVE"
  fi
fi

mkdir -p -- "$(dirname -- "$OUTPUT")"
TMP_OUTPUT="$(mktemp -p "$(dirname -- "$OUTPUT")" "$(basename -- "$OUTPUT").tmp.XXXXXX")"

tar_stream() {
  if [[ -z "$(find "$WORKDIR" -mindepth 1 -print -quit)" ]]; then
    tar --numeric-owner -C "$WORKDIR" -cf - --files-from /dev/null
  else
    tar --numeric-owner -C "$WORKDIR" -cf - .
  fi
}

log "Creating tar.zst at $OUTPUT ..."
if [[ "$ARCHIVE_TYPE" == "7z" ]]; then
  if ! tar_stream | "$ZEEKSTD_BIN" "${ZEEKSTD_ARGS[@]}" -o "$TMP_OUTPUT"; then
    die "zeekstd compression failed"
  fi
else
  log "Streaming $ARCHIVE via $INPUT_STREAM_DESC ..."
  if ! "${INPUT_STREAM_CMD[@]}" | "$ZEEKSTD_BIN" "${ZEEKSTD_ARGS[@]}" -o "$TMP_OUTPUT"; then
    die "zeekstd compression failed"
  fi
fi

if [[ -e "$OUTPUT" && "$FORCE" -eq 1 ]]; then
  rm -f -- "$OUTPUT"
fi
mv -f -- "$TMP_OUTPUT" "$OUTPUT"
TMP_OUTPUT=""

if ! touch -r "$ARCHIVE" "$OUTPUT"; then
  die "Failed to copy modification time to $OUTPUT"
fi

if [[ "$REMOVE_SOURCE" -eq 1 ]]; then
  log "Removing source archive: $ARCHIVE"
  rm -f -- "$ARCHIVE"
fi

if [[ "$SHA256_ENABLED" -eq 1 ]]; then
  write_sha256_manifest "$WORKDIR" "$SHA256_FILE"
fi

log "Conversion complete: $OUTPUT"

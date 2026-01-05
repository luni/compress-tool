#!/usr/bin/env bash
set -euo pipefail

SUITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd "$SUITE_DIR/.." && pwd)"
source "$TEST_ROOT/lib/common.sh"
trap cleanup_tmpdirs EXIT

# Use new command group requirements
require_parallel_commands
require_compression_commands
require_basic_commands
require_cmd sha1sum

run_single_compress_test() {
  local small_comp="$1" big_comp="$2" label="$3" big_jobs="${4:-1}"
  run_standard_test "compress.sh test (${label})" _run_single_compress_test "$small_comp" "$big_comp" "$label" "$big_jobs"
}

_run_single_compress_test() {
  local tmpdir="$1"
  local small_comp="$2"
  local big_comp="$3"
  local label="$4"
  local big_jobs="$5"
  local threshold_bytes=$((2 * 1024))
  local sha1_file="$tmpdir/checksums.sha1"
  local sha256_file="$tmpdir/checksums.sha256"

  # Use standard fixture - this is the main refactoring benefit
  local hash_output
  hash_output="$(create_standard_fixture "$tmpdir" "COMPRESSION" "Compression fixture ($label)")"

  # Parse hash output and create test data
  local -a fixture_paths
  local -A expected_paths sha1_map sha256_map source_paths size_map

  # Define sizes for COMPRESSION fixture
  declare -A compression_sizes=(
    ["small.txt"]=512
    ["sub dir/medium file.txt"]=1536
    ["big data/bigfile.sql"]=65536
    ["special chars/über@Data!.txt"]=98304
  )

  while IFS='=' read -r path hash; do
    fixture_paths+=("$path")
    expected_paths["$path"]="$tmpdir/${path}.expected"
    source_paths["$path"]="$tmpdir/$path"
    size_map["$path"]="${compression_sizes[$path]}"
    sha1_map["$path"]="$(sha1sum -- "$tmpdir/$path" | awk '{print $1}')"
    sha256_map["$path"]="$(sha256sum -- "$tmpdir/$path" | awk '{print $1}')"
    cp -- "$tmpdir/$path" "${expected_paths[$path]}"
  done <<<"$hash_output"

  local output
  if ! output="$("$COMPRESS_SCRIPT" \
      --dir "$tmpdir" \
      --jobs 2 \
      --small "$small_comp" \
      --big "$big_comp" \
      --big-jobs "$big_jobs" \
      --threshold "$threshold_bytes" \
      --sha1 "$sha1_file" \
      --sha256 "$sha256_file" 2>&1)"; then
    echo "compress.sh failed (${label})" >&2
    echo "$output" >&2
    return 1
  fi

  if [[ "$output" != *"big(${big_comp})"* ]]; then
    echo "Expected big-file compression path (${big_comp}) to run" >&2
    echo "$output" >&2
    return 1
  fi

  local sha1_args=()
  local sha256_args=()

  for path in "${fixture_paths[@]}"; do
    local original_path="${source_paths[$path]}"
    if [[ -f "$original_path" ]]; then
      echo "Expected original file to be removed after compression: $path" >&2
      return 1
    fi

    local size="${size_map[$path]}"
    local compressor="$small_comp"
    if [[ "$size" -ge "$threshold_bytes" ]]; then
      compressor="$big_comp"
    fi

    local compressed_rel
    compressed_rel="$(compressed_name_for "$path" "$compressor")"
    local compressed="$tmpdir/$compressed_rel"

    if [[ ! -f "$compressed" ]]; then
      echo "Compressed file not created: $compressed" >&2
      return 1
    fi

    local decompressed="$tmpdir/${path}.dec"
    decompress_with "$compressor" "$compressed" "$decompressed"
    if ! cmp -s "${expected_paths[$path]}" "$decompressed"; then
      echo "Compressed file contents mismatch for $path (${compressor})" >&2
      return 1
    fi

    sha1_args+=("${source_paths[$path]}" "${sha1_map[$path]}")
    sha256_args+=("${source_paths[$path]}" "${sha256_map[$path]}")
  done

  verify_checksum_file "$sha1_file" "${sha1_args[@]}"
  verify_checksum_file "$sha256_file" "${sha256_args[@]}"
}

run_compress_suite() {
  run_single_compress_test xz xz "xz-only"
  run_single_compress_test zstd zstd "zstd-only"
  run_single_compress_test zstd zstd "zstd-big-parallel" 2
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  run_compress_suite "$@"
fi

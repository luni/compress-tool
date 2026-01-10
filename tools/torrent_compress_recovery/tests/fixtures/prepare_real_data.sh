#!/bin/bash
# Prepare realistic test data for torrent-compress-recovery

set -e

HERE="$(dirname "$0")"
DATA_DIR="$(realpath "$HERE/real_data")"
RAW_DIR="$DATA_DIR/raw"
PARTIAL_DIR="$DATA_DIR/partial"

# Create directories
mkdir -p "$RAW_DIR" "$PARTIAL_DIR"

# Create raw files
echo "This is a readme file." > "$RAW_DIR/readme.txt"
python3 -c "import sys; sys.stdout.buffer.write(bytes(range(256)))" > "$RAW_DIR/data.bin"
echo '{"key": "value", "number": 42}' > "$RAW_DIR/config.json"

# Gzip them with deterministic settings (gzip -n -6)
for name in readme.txt data.bin config.json; do
    gzip -n -6 -c "$RAW_DIR/$name" > "$DATA_DIR/$name.gz"
done

# Create pigz-compressed versions with different settings
if command -v pigz >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # pigz with different compression levels and options
        pigz -1 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pigz1.gz"
        pigz -6 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pigz6.gz"
        pigz -9 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pigz9.gz"
        pigz -6 --rsyncable -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pigz_rsync.gz"
    done
    echo "Created pigz compressed files"
else
    echo "pigz not available, skipping pigz test data"
fi

# Create bzip2-compressed versions with different settings
if command -v bzip2 >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # bzip2 with different compression levels
        bzip2 -1 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.bz1.bz2"
        bzip2 -6 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.bz6.bz2"
        bzip2 -9 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.bz9.bz2"
    done
    echo "Created bzip2 compressed files"
else
    echo "bzip2 not available, skipping bzip2 test data"
fi

# Create pbzip2-compressed versions with different settings
if command -v pbzip2 >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # pbzip2 with different compression levels
        pbzip2 -1 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pbz1.bz2"
        pbzip2 -6 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pbz6.bz2"
        pbzip2 -9 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pbz9.bz2"
    done
    echo "Created pbzip2 compressed files"
else
    echo "pbzip2 not available, skipping pbzip2 test data"
fi

# Create xz-compressed versions with different settings
if command -v xz >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # xz with different compression levels
        xz -0 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.xz0.xz"
        xz -6 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.xz6.xz"
        xz -9 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.xz9.xz"
    done
    echo "Created xz compressed files"
else
    echo "xz not available, skipping xz test data"
fi

# Create pixz-compressed versions with different settings
if command -v pixz >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # pixz with different compression levels - use cat to avoid file removal
        cat "$RAW_DIR/$name" | pixz -0 -c > "$DATA_DIR/${name}.pixz0.xz"
        cat "$RAW_DIR/$name" | pixz -6 -c > "$DATA_DIR/${name}.pixz6.xz"
        cat "$RAW_DIR/$name" | pixz -9 -c > "$DATA_DIR/${name}.pixz9.xz"
    done
    echo "Created pixz compressed files"
else
    echo "pixz not available, skipping pixz test data"
fi

# Create zstd-compressed versions with different settings
if command -v zstd >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # zstd with different compression levels (max is 19)
        zstd -1 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.zst1.zst"
        zstd -3 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.zst3.zst"
        zstd -19 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.zst19.zst"
    done
    echo "Created zstd compressed files"
else
    echo "zstd not available, skipping zstd test data"
fi

# Create pzstd-compressed versions with different settings
if command -v pzstd >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # pzstd with different compression levels (max is 19)
        pzstd -1 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pzstd1.zst"
        pzstd -3 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pzstd3.zst"
        pzstd -19 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pzstd19.zst"
    done
    echo "Created pzstd compressed files"
else
    echo "pzstd not available, skipping pzstd test data"
fi

# Create truncated partial copies (first half)
mkdir -p "$PARTIAL_DIR"
for gz_file in "$DATA_DIR"/*.gz "$DATA_DIR"/*.bz2 "$DATA_DIR"/*.xz "$DATA_DIR"/*.zst; do
    if [ -f "$gz_file" ]; then
        partial_file="$PARTIAL_DIR/$(basename "$gz_file")"
        head -c "$(($(wc -c < "$gz_file") / 2))" "$gz_file" > "$partial_file"
    fi
done

# Create test data for overlapping pieces and offset files
OVERLAP_DIR="$DATA_DIR/overlap_test"
OVERLAP_RAW_DIR="$OVERLAP_DIR/raw"
OVERLAP_PARTIAL_DIR="$OVERLAP_DIR/partial"
mkdir -p "$OVERLAP_RAW_DIR" "$OVERLAP_PARTIAL_DIR"

# Create files with specific sizes to create overlapping scenarios
# File 1: 25 bytes (spans 2 pieces with 16-byte piece length)
echo "This is file one with 25 bytes" > "$OVERLAP_RAW_DIR/file1.txt"

# File 2: 30 bytes (spans 2 pieces, overlapping with file1)
echo "This is file two with 30 bytes!" > "$OVERLAP_RAW_DIR/file2.txt"

# File 3: 10 bytes (fits in one piece)
echo "File three" > "$OVERLAP_RAW_DIR/file3.txt"

# File 4: 40 bytes (spans 3 pieces)
echo "This is file four with exactly forty bytes total" > "$OVERLAP_RAW_DIR/file4.txt"

# Compress the overlap test files
for name in file1.txt file2.txt file3.txt file4.txt; do
    gzip -n -6 -c "$OVERLAP_RAW_DIR/$name" > "$OVERLAP_DIR/$name.gz"
done

# Create partial files with different offsets to simulate overlapping pieces
# Simulate file1 starting at offset 0 (piece boundary)
cp "$OVERLAP_DIR/file1.txt.gz" "$OVERLAP_PARTIAL_DIR/"

# Simulate file2 starting at offset 5 (5 bytes into first piece)
# We'll create a modified version that starts 5 bytes into the piece
dd if="$OVERLAP_DIR/file2.txt.gz" of="$OVERLAP_PARTIAL_DIR/file2_offset5.gz" bs=1 skip=5 2>/dev/null || true

# Simulate file3 starting at offset 12 (near end of first piece)
dd if="$OVERLAP_DIR/file3.txt.gz" of="$OVERLAP_PARTIAL_DIR/file3_offset12.gz" bs=1 skip=12 2>/dev/null || true

# Create torrent with small piece length to force overlapping
OVERLAP_COMPRESSED_DIR="$OVERLAP_DIR/compressed_temp"
mkdir -p "$OVERLAP_COMPRESSED_DIR"
cp "$OVERLAP_DIR"/*.gz "$OVERLAP_COMPRESSED_DIR/" 2>/dev/null || true

cd "$(dirname "$0")/../.."
uv run torrentfile create \
    --announce "http://localhost:6969/announce" \
    --piece-length 16 \
    --comment "overlap-test-small-pieces" \
    --out "$OVERLAP_DIR/overlap_small_pieces.torrent" \
    "$OVERLAP_COMPRESSED_DIR"

# Create another torrent with even smaller pieces for more complex overlapping
uv run torrentfile create \
    --announce "http://localhost:6969/announce" \
    --piece-length 32 \
    --comment "overlap-test-medium-pieces" \
    --out "$OVERLAP_DIR/overlap_medium_pieces.torrent" \
    "$OVERLAP_COMPRESSED_DIR"

# Clean up temporary directory
rm -rf "$OVERLAP_COMPRESSED_DIR"

# Create a torrent with files that have manual offsets (using padding files)
PADDING_DIR="$DATA_DIR/padding_test"
PADDING_RAW_DIR="$PADDING_DIR/raw"
PADDING_COMPRESSED_DIR="$PADDING_DIR/compressed"
mkdir -p "$PADDING_RAW_DIR" "$PADDING_COMPRESSED_DIR"

# Create a padding file to offset the real files
echo "PADDING_DATA_TO_OFFSET_FILES" > "$PADDING_RAW_DIR/padding.txt"

# Create real files
echo "Real content one" > "$PADDING_RAW_DIR/real1.txt"
echo "Real content two" > "$PADDING_RAW_DIR/real2.txt"

# Compress all files
for name in padding.txt real1.txt real2.txt; do
    gzip -n -6 -c "$PADDING_RAW_DIR/$name" > "$PADDING_COMPRESSED_DIR/$name.gz"
done

uv run torrentfile create \
    --announce "http://localhost:6969/announce" \
    --piece-length 16 \
    --comment "padding-offset-test" \
    --out "$PADDING_DIR/padding_offset.torrent" \
    "$PADDING_COMPRESSED_DIR"

echo "Created overlapping pieces test data:"
echo "Overlap test dir: $OVERLAP_DIR"
echo "Padding test dir: $PADDING_DIR"
echo "Small pieces torrent: $OVERLAP_DIR/overlap_small_pieces.torrent"
echo "Medium pieces torrent: $OVERLAP_DIR/overlap_medium_pieces.torrent"
echo "Padding offset torrent: $PADDING_DIR/padding_offset.torrent"

# Create torrent using torrentfile CLI (supports v1, v2, and hybrid)

# Create a temporary directory with only the compressed files for torrentfile
COMPRESSED_ONLY_DIR="$DATA_DIR/compressed_only_temp"
mkdir -p "$COMPRESSED_ONLY_DIR"
cp "$DATA_DIR"/*.gz "$DATA_DIR"/*.bz2 "$DATA_DIR"/*.xz "$DATA_DIR"/*.zst "$COMPRESSED_ONLY_DIR/" 2>/dev/null || true

uv run torrentfile create \
    --announce "http://localhost:6969/announce" \
    --piece-length 20 \
    --comment "torrent-compress-recovery-test-generator" \
    --out "$DATA_DIR/sample.torrent" \
    "$COMPRESSED_ONLY_DIR"

# Clean up the temporary directory
rm -rf "$COMPRESSED_ONLY_DIR"

echo "Prepared realistic test data in $DATA_DIR"
echo "Raw files: $(ls -1 "$RAW_DIR" 2>/dev/null | tr '\n' ' ' || echo "none")"
echo "Gz files: $(ls -1 "$DATA_DIR"/*.gz 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ' || echo "none")"
echo "Bz2 files: $(ls -1 "$DATA_DIR"/*.bz2 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ' || echo "none")"
echo "Xz files: $(ls -1 "$DATA_DIR"/*.xz 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ' || echo "none")"
echo "Zst files: $(ls -1 "$DATA_DIR"/*.zst 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ' || echo "none")"
echo "Partial files: $(ls -1 "$PARTIAL_DIR" 2>/dev/null | tr '\n' ' ' || echo "none")"
echo "Torrent: $DATA_DIR/sample.torrent"
echo ""
echo "Overlapping pieces test data:"
echo "- Small pieces torrent (16-byte pieces): $OVERLAP_DIR/overlap_small_pieces.torrent"
echo "- Medium pieces torrent (32-byte pieces): $OVERLAP_DIR/overlap_medium_pieces.torrent"
echo "- Padding offset torrent: $PADDING_DIR/padding_offset.torrent"
echo "- Overlap test files: $(ls -1 "$OVERLAP_DIR"/*.gz 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ' || echo "none")"

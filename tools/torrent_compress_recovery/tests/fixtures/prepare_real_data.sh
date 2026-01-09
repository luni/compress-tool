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
        # pixz with different compression levels
        pixz -0 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pixz0.xz"
        pixz -6 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pixz6.xz"
        pixz -9 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pixz9.xz"
    done
    echo "Created pixz compressed files"
else
    echo "pixz not available, skipping pixz test data"
fi

# Create zstd-compressed versions with different settings
if command -v zstd >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # zstd with different compression levels
        zstd -1 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.zst1.zst"
        zstd -3 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.zst3.zst"
        zstd -22 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.zst22.zst"
    done
    echo "Created zstd compressed files"
else
    echo "zstd not available, skipping zstd test data"
fi

# Create pzstd-compressed versions with different settings
if command -v pzstd >/dev/null 2>&1; then
    for name in readme.txt data.bin config.json; do
        # pzstd with different compression levels
        pzstd -1 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pzstd1.zst"
        pzstd -3 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pzstd3.zst"
        pzstd -22 -c "$RAW_DIR/$name" > "$DATA_DIR/${name}.pzstd22.zst"
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

# Create torrent using torrentfile CLI (supports v1, v2, and hybrid)
cd "$(dirname "$0")/../.."

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

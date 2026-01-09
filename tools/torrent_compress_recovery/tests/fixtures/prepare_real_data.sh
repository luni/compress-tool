#!/bin/bash
# Prepare realistic test data for torrent-compress-recovery

set -e

HERE="$(dirname "$0")"
DATA_DIR="$HERE/real_data"
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

# Create truncated partial copies (first half)
for gz_file in "$DATA_DIR"/*.gz; do
    partial_file="$PARTIAL_DIR/$(basename "$gz_file")"
    head -c "$(($(wc -c < "$gz_file") / 2))" "$gz_file" > "$partial_file"
done

# Create torrent using ctorrent
cd "$DATA_DIR"

# Create a subdirectory with only the gz files for ctorrent
GZ_ONLY_DIR="$DATA_DIR/gz_only"
mkdir -p "$GZ_ONLY_DIR"
cp *.gz "$GZ_ONLY_DIR/"

# Run ctorrent to create torrent from directory
cd "$GZ_ONLY_DIR"
ctorrent -t -s ../sample.torrent -u http://localhost:6969/announce -l 65536 .

# Clean up the temporary directory
cd ..
rm -rf "$GZ_ONLY_DIR"

echo "Prepared realistic test data in $DATA_DIR"
echo "Raw files: $(ls -1 "$RAW_DIR" 2>/dev/null || echo "none")"
echo "Gz files: $(ls -1 "$DATA_DIR"/*.gz 2>/dev/null | xargs -n1 basename 2>/dev/null || echo "none")"
echo "Partial files: $(ls -1 "$PARTIAL_DIR" 2>/dev/null || echo "none")"
echo "Torrent: $DATA_DIR/sample.torrent"

#!/usr/bin/env python3
"""Prepare realistic test data for torrent-compress-recovery."""

import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

HERE = Path(__file__).parent
DATA_DIR = HERE / "real_data"
DATA_DIR.mkdir(exist_ok=True)
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(exist_ok=True)
PARTIAL_DIR = DATA_DIR / "partial"
PARTIAL_DIR.mkdir(exist_ok=True)

# Create some raw files
files = {
    "readme.txt": b"This is a readme file.\n",
    "data.bin": bytes(range(256)),
    "config.json": b'{"key": "value", "number": 42}\n',
}
for name, content in files.items():
    (RAW_DIR / name).write_bytes(content)

# Gzip them with deterministic settings (gzip -n -6)
for name in files:
    gz_path = DATA_DIR / f"{name}.gz"
    subprocess.run(
        ["gzip", "-n", "-6", "-c", str(RAW_DIR / name)],
        stdout=open(gz_path, "wb"),
        check=True,
    )

# Create truncated partial copies (first half)
for gz_path in DATA_DIR.glob("*.gz"):
    partial = PARTIAL_DIR / gz_path.name
    data = gz_path.read_bytes()
    partial.write_bytes(data[: len(data) // 2])

# Create torrent using ctorrent
all_gz = list(DATA_DIR.glob("*.gz"))
if not all_gz:
    logging.error("No .gz files found to create torrent")
    sys.exit(1)

# Create a subdirectory with only the gz files for ctorrent
GZ_ONLY_DIR = DATA_DIR / "gz_only"
GZ_ONLY_DIR.mkdir(exist_ok=True)
for gz in all_gz:
    import shutil
    shutil.copy2(gz, GZ_ONLY_DIR / gz.name)

# Change to data directory for ctorrent
old_cwd = os.getcwd()
try:
    os.chdir(GZ_ONLY_DIR)

    # Run ctorrent to create torrent from directory
    cmd = [
        "ctorrent",
        "-t",  # Create a new torrent file
        "-s", "../sample.torrent",  # Output file in parent
        "-u", "http://localhost:6969/announce",  # Dummy announce URL
        "-l", "65536",  # Piece length (64KB, minimum for ctorrent)
        ".",  # Current directory (contains only gz files)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    torrent_path = DATA_DIR / "sample.torrent"

finally:
    os.chdir(old_cwd)
    # Clean up the temporary directory
    import shutil
    shutil.rmtree(GZ_ONLY_DIR, ignore_errors=True)

logging.info(f"Prepared realistic test data in {DATA_DIR}")
logging.info(f"Raw files: {list(RAW_DIR.iterdir())}")
logging.info(f"Gz files: {list(DATA_DIR.glob('*.gz'))}")
logging.info(f"Partial files: {list(PARTIAL_DIR.iterdir())}")
logging.info(f"Torrent: {torrent_path}")

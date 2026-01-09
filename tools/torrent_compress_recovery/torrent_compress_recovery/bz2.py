"""Bzip2 header parsing and brute-force generation utilities."""

import bz2
import hashlib
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

# Bzip2 format constants
BZIP2_MAGIC = b"BZh"
BZIP2_HEADER_SIZE = 4
BZIP2_MIN_LEVEL = 1
BZIP2_MAX_LEVEL = 9
BZIP2_LEVEL_BYTE_POS = 3  # Position of compression level byte in header

# Bzip2 block sizes (100k * level)
BZIP2_BLOCK_SIZES = {level: level * 100000 for level in range(BZIP2_MIN_LEVEL, BZIP2_MAX_LEVEL + 1)}


@dataclass(frozen=True)
class Bzip2Header:
    """Bzip2 header information (limited compared to gzip)."""

    # Bzip2 has a very simple header format:
    # Magic: "BZh" + compression level (1-9)
    # Block size: 100k * level
    # No timestamp, filename, or other metadata like gzip
    level: int  # Compression level (1-9)
    block_size: int  # Block size in bytes


def _get_block_size_description(level: int) -> str:
    """Get human-readable block size description."""
    block_size = BZIP2_BLOCK_SIZES.get(level, 0)
    return f"{block_size:,} bytes ({block_size / 1000:.0f} KB)"


def parse_bzip2_header(path: Path) -> Bzip2Header | None:
    """Parse the bzip2 header from a file."""
    with path.open("rb") as f:
        data = f.read(BZIP2_HEADER_SIZE)  # enough for header
    if len(data) < BZIP2_HEADER_SIZE or not data.startswith(BZIP2_MAGIC):
        return None

    # Extract compression level from the 4th byte
    if len(data) < BZIP2_HEADER_SIZE or data[BZIP2_LEVEL_BYTE_POS] < ord(str(BZIP2_MIN_LEVEL)) or data[BZIP2_LEVEL_BYTE_POS] > ord(str(BZIP2_MAX_LEVEL)):
        return None

    level = int(data[BZIP2_LEVEL_BYTE_POS : BZIP2_LEVEL_BYTE_POS + 1].decode("ascii"))
    block_size = BZIP2_BLOCK_SIZES.get(level, 0)
    return Bzip2Header(level=level, block_size=block_size)


def format_bzip2_header(header: Bzip2Header) -> str:
    """Return a human-readable summary of bzip2 header fields."""
    lines = [
        f"compression level: {header.level}",
        f"block size: {_get_block_size_description(header.level)}",
    ]
    return "\n".join(lines)


def patch_bzip2_header(data: bytes, header: Bzip2Header) -> bytes:
    """Patch bzip2 header to match the provided header (compression level)."""
    if len(data) < BZIP2_HEADER_SIZE or not data.startswith(BZIP2_MAGIC):
        return data

    # Replace the compression level byte
    patched = bytearray(data)
    patched[BZIP2_LEVEL_BYTE_POS] = ord(str(header.level))
    return bytes(patched)


def sha1_piece(data: bytes) -> bytes:
    """Return SHA-1 hash of data."""
    return hashlib.sha1(data).digest()


def generate_bzip2_candidates(src: Path, header: Bzip2Header | None) -> list[tuple[str, bytes]]:
    """Generate candidate bzip2 bytes for a source file using common tools/settings."""
    candidates: list[tuple[str, bytes]] = []
    src_bytes = src.read_bytes()

    # 1) Try to match header settings if available
    if header:
        # Use python bz2 with exact compression level
        try:
            data = bz2.compress(src_bytes, compresslevel=header.level)
            candidates.append(("header_match", data))
        except (OSError, ValueError):
            # Handle compression errors gracefully
            pass

    # 2) Brute-force common tools/levels
    tools = ["bzip2"]
    try:
        subprocess.run(["pbzip2", "-h"], check=True, capture_output=True)  # nosec B603, B607
        tools.append("pbzip2")
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    for tool in tools:
        for level in [BZIP2_MIN_LEVEL, 6, BZIP2_MAX_LEVEL]:
            if tool == "bzip2":
                cmd = ["bzip2", f"-{level}", "-c", str(src)]
            else:  # pbzip2
                cmd = ["pbzip2", f"-{level}", "-c", str(src)]

            try:
                proc = subprocess.run(cmd, check=True, capture_output=True)  # nosec B603
                data = proc.stdout
                label = f"{tool} -{level}"
                candidates.append((label, data))
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue

    return candidates


def sha256_piece(data: bytes) -> bytes:
    """Return SHA-256 hash of data."""
    return hashlib.sha256(data).digest()


def find_matching_candidate(
    candidates: list[tuple[str, bytes]],
    target_piece_hash: bytes,
    piece_length: int,
    hash_algo: str = "sha1",
) -> tuple[str, bytes] | None:
    """Return the first candidate whose first piece hash matches."""
    hash_fn = sha1_piece if hash_algo == "sha1" else sha256_piece
    for label, data in candidates:
        if len(data) < piece_length:
            continue
        piece = data[:piece_length]
        if hash_fn(piece) == target_piece_hash:
            return label, data
    return None

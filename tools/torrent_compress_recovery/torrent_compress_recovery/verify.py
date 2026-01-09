"""Step B: Verify raw files against compression trailers using last piece."""

import subprocess  # nosec B404
import zlib
from pathlib import Path

from .bencode import parse_torrent

# Gzip trailer constants
GZIP_TRAILER_SIZE = 8
GZIP_CRC32_SIZE = 4
GZIP_ISIZE_SIZE = 4

# XZ stream footer constants
XZ_FOOTER_SIZE = 12
XZ_FOOTER_MAGIC = b"\x59\x5a"

# Zstandard frame footer constants
ZSTD_FRAME_FOOTER_SIZE = 4


def read_gzip_trailer(path: Path) -> tuple[int, int] | None:
    """Read CRC32 and ISIZE from the last 8 bytes of a gzip file."""
    # Check file size first - files smaller than 8 bytes are broken
    file_size = path.stat().st_size
    if file_size < GZIP_TRAILER_SIZE:
        return None

    with path.open("rb") as f:
        f.seek(-GZIP_TRAILER_SIZE, 2)  # Seek 8 bytes from end
        trailer = f.read()
    if len(trailer) != GZIP_TRAILER_SIZE:
        return None
    crc32 = int.from_bytes(trailer[:GZIP_CRC32_SIZE], "little")
    isize = int.from_bytes(trailer[GZIP_CRC32_SIZE:], "little")
    return crc32, isize


def compute_raw_crc32_and_isize(raw_path: Path) -> tuple[int, int]:
    """Compute CRC32 and size (mod 2^32) of raw data."""
    crc = 0
    size = 0
    with raw_path.open("rb") as f:
        while chunk := f.read(8192):
            crc = zlib.crc32(chunk, crc) & 0xFFFFFFFF
            size += len(chunk)
    return crc, size & 0xFFFFFFFF


def verify_raw_against_gz(raw_path: Path, gz_path: Path) -> bool:
    """Verify raw file matches gzip trailer (CRC32/ISIZE)."""
    trailer = read_gzip_trailer(gz_path)
    if trailer is None:
        return False
    gz_crc32, gz_isize = trailer
    raw_crc32, raw_isize = compute_raw_crc32_and_isize(raw_path)
    return gz_crc32 == raw_crc32 and gz_isize == raw_isize


def read_xz_footer(path: Path) -> tuple[int, int] | None:
    """Read CRC32 and backward size from the last 12 bytes of an XZ file."""
    # Check file size first - files smaller than 12 bytes are broken
    file_size = path.stat().st_size
    if file_size < XZ_FOOTER_SIZE:
        return None

    with path.open("rb") as f:
        f.seek(-XZ_FOOTER_SIZE, 2)  # Seek 12 bytes from end
        footer = f.read()
    if len(footer) != XZ_FOOTER_SIZE:
        return None

    # Check magic bytes
    if footer[-2:] != XZ_FOOTER_MAGIC:
        return None

    # Extract CRC32 (first 4 bytes) and backward size (next 4 bytes)
    crc32 = int.from_bytes(footer[:4], "little")
    backward_size = int.from_bytes(footer[4:8], "little") + 1  # Stored size is -1

    return crc32, backward_size


def verify_raw_against_xz(raw_path: Path, xz_path: Path) -> bool:
    """Verify raw file matches XZ footer (basic validation)."""
    # For XZ, we'll do a basic check by decompressing and comparing
    # This is a simplified verification - real XZ verification is more complex
    try:
        # Try to decompress and compare sizes
        result = subprocess.run(["/usr/bin/xz", "-dc", str(xz_path)], capture_output=True, check=True)  # nosec B603
        decompressed = result.stdout
        raw_data = raw_path.read_bytes()
        return decompressed == raw_data
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def read_zstd_footer(path: Path) -> tuple[int, int] | None:
    """Read checksum and dictionary ID from the last 4 bytes of a Zstandard frame."""
    # Check file size first - files smaller than 4 bytes are broken
    file_size = path.stat().st_size
    if file_size < ZSTD_FRAME_FOOTER_SIZE:
        return None

    with path.open("rb") as f:
        f.seek(-ZSTD_FRAME_FOOTER_SIZE, 2)  # Seek 4 bytes from end
        footer = f.read()
    if len(footer) != ZSTD_FRAME_FOOTER_SIZE:
        return None

    # Extract checksum (last 4 bytes, little-endian)
    # Note: This is a simplified approach - real Zstd has more complex footer structure
    checksum = int.from_bytes(footer, "little")

    return checksum, 0  # Return dummy second value for consistency


def verify_raw_against_zst(raw_path: Path, zst_path: Path) -> bool:
    """Verify raw file matches Zstandard frame (basic validation)."""
    # For Zstd, we'll do a basic check by decompressing and comparing
    try:
        # Try to decompress and compare sizes
        result = subprocess.run(["/usr/bin/zstd", "-dc", str(zst_path)], capture_output=True, check=True)  # nosec B603
        decompressed = result.stdout
        raw_data = raw_path.read_bytes()
        return decompressed == raw_data
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def verify_last_piece_against_raw(torrent_path: Path, raw_dir: Path, partial_dir: Path) -> dict[str, bool]:
    """
    For each compressed file in the torrent, if the last piece exists in partial_dir,
    extract the footer/trailer and compare to the corresponding raw file.
    Returns a mapping from filename to verification result.
    """
    meta = parse_torrent(str(torrent_path))
    results: dict[str, bool] = {}
    for tf in meta.files:
        if not tf.rel_path.endswith((".gz", ".bz2", ".xz", ".zst")):
            continue

        filename = Path(tf.rel_path).name
        partial_file = partial_dir / filename
        if not partial_file.is_file():
            continue

        # Determine if we have the last piece (file size >= tf.length)
        if tf.length is None:
            continue
        if partial_file.stat().st_size < tf.length:
            continue

        # Find corresponding raw file
        if tf.rel_path.endswith(".gz"):
            raw_name = filename[: -len(".gz")]
            verify_func = verify_raw_against_gz
        elif tf.rel_path.endswith(".bz2"):
            raw_name = filename[: -len(".bz2")]
            # For bzip2, we don't have a simple verification like gzip
            # We'll skip bzip2 verification for now
            continue
        elif tf.rel_path.endswith(".xz"):
            raw_name = filename[: -len(".xz")]
            verify_func = verify_raw_against_xz
        elif tf.rel_path.endswith(".zst"):
            raw_name = filename[: -len(".zst")]
            verify_func = verify_raw_against_zst
        else:
            continue

        raw_path = raw_dir / raw_name
        if not raw_path.is_file():
            results[filename] = False
            continue

        results[filename] = verify_func(raw_path, partial_file)

    return results

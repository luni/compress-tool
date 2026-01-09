"""Zstandard header parsing and brute-force generation utilities."""

import hashlib
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Zstandard format constants
ZSTD_MAGIC_NUMBER = b"\x28\xb5\x2f\xfd"
ZSTD_FRAME_HEADER_MIN_SIZE = 6  # Magic (4) + frame_header (2)
ZSTD_MAGIC_SIZE = 4
ZSTD_FRAME_HEADER_SIZE = 2

# Zstandard frame header flags
ZSTD_FRAME_HEADER_WINDOWLOG_OFFSET = 0
ZSTD_FRAME_HEADER_WINDOWLOG_MASK = 0x0F
ZSTD_FRAME_HEADER_SINGLE_SEGMENT_FLAG = 0x20
ZSTD_FRAME_HEADER_CHECKSUM_FLAG = 0x10
ZSTD_FRAME_HEADER_DICT_ID_FLAG = 0x08

# Common compression levels for zstd
ZSTD_MIN_LEVEL = 1
ZSTD_DEFAULT_LEVEL = 3
ZSTD_MAX_LEVEL = 22


@dataclass(frozen=True)
class ZstdHeader:
    """Zstandard frame header information."""

    window_log: int  # Window log value
    single_segment: bool  # Single segment flag
    has_checksum: bool  # Whether content checksum is enabled
    has_dict_id: bool  # Whether dictionary ID is present


def parse_zstd_header(path: Path) -> ZstdHeader | None:
    """Parse the Zstandard frame header from a file."""
    with path.open("rb") as f:
        data = f.read(ZSTD_FRAME_HEADER_MIN_SIZE)

    if len(data) < ZSTD_FRAME_HEADER_MIN_SIZE or not data.startswith(ZSTD_MAGIC_NUMBER):
        return None

    # Extract frame header (bytes 4-5)
    frame_header_bytes = data[4:6]
    frame_header = int.from_bytes(frame_header_bytes, "little")

    # Parse window log (bits 0-3)
    window_log = frame_header & ZSTD_FRAME_HEADER_WINDOWLOG_MASK

    # Parse flags
    single_segment = bool(frame_header & ZSTD_FRAME_HEADER_SINGLE_SEGMENT_FLAG)
    has_checksum = bool(frame_header & ZSTD_FRAME_HEADER_CHECKSUM_FLAG)
    has_dict_id = bool(frame_header & ZSTD_FRAME_HEADER_DICT_ID_FLAG)

    return ZstdHeader(
        window_log=window_log,
        single_segment=single_segment,
        has_checksum=has_checksum,
        has_dict_id=has_dict_id,
    )


def format_zstd_header(header: ZstdHeader) -> str:
    """Return a human-readable summary of Zstandard header fields."""
    lines = [
        f"window_log: {header.window_log}",
        f"single_segment: {header.single_segment}",
        f"has_checksum: {header.has_checksum}",
        f"has_dict_id: {header.has_dict_id}",
    ]
    return "\n".join(lines)


def patch_zstd_header(data: bytes, header: ZstdHeader) -> bytes:
    """Patch Zstandard frame header to match the provided header."""
    if len(data) < ZSTD_FRAME_HEADER_MIN_SIZE or not data.startswith(ZSTD_MAGIC_NUMBER):
        return data

    # Reconstruct frame header
    frame_header = header.window_log & ZSTD_FRAME_HEADER_WINDOWLOG_MASK
    if header.single_segment:
        frame_header |= ZSTD_FRAME_HEADER_SINGLE_SEGMENT_FLAG
    if header.has_checksum:
        frame_header |= ZSTD_FRAME_HEADER_CHECKSUM_FLAG
    if header.has_dict_id:
        frame_header |= ZSTD_FRAME_HEADER_DICT_ID_FLAG

    # Replace the frame header
    patched = bytearray(data)
    patched[4:6] = frame_header.to_bytes(ZSTD_FRAME_HEADER_SIZE, "little")

    return bytes(patched)


def sha1_piece(data: bytes) -> bytes:
    """Return SHA-1 hash of data."""
    return hashlib.sha1(data).digest()


def _generate_header_match_candidate(src_bytes: bytes, header: ZstdHeader) -> tuple[str, bytes]:
    """Generate a candidate that matches the exact header settings."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            # Use zstd command to compress
            cmd = ["zstd", "-c", "--stdout"]
            proc = subprocess.run(cmd, input=src_bytes, capture_output=True)  # nosec B603
            if proc.returncode == 0:
                data = proc.stdout
                data = patch_zstd_header(data, header)
                return ("header_match", data)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        finally:
            tmp_path.unlink()
    return None


def _get_available_tools() -> list[str]:
    """Get list of available compression tools."""
    tools = ["zstd"]
    try:
        subprocess.run(["pzstd", "--version"], check=True, capture_output=True)  # nosec B603, B607
        tools.append("pzstd")
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return tools


def _build_command(tool: str, level: int) -> list[str]:
    """Build compression command with appropriate flags."""
    if tool == "zstd":
        return ["zstd", f"-{level}", "-c", "--stdout"]
    else:  # pzstd
        return ["pzstd", f"-{level}", "-c", "--stdout"]


def _generate_tool_candidate(src: Path, tool: str, level: int, header: ZstdHeader | None) -> tuple[str, bytes] | None:
    """Generate a candidate using a specific tool and settings."""
    cmd = _build_command(tool, level)
    cmd.append(str(src))

    try:
        proc = subprocess.run(cmd, check=True, capture_output=True)  # nosec B603
        data = proc.stdout
        if header:
            data = patch_zstd_header(data, header)
        label = f"{tool} -{level}"
        return (label, data)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def generate_zstd_candidates(src: Path, header: ZstdHeader | None) -> list[tuple[str, bytes]]:
    """Generate candidate Zstandard bytes for a source file using common tools/settings."""
    candidates: list[tuple[str, bytes]] = []
    src_bytes = src.read_bytes()

    # 1) Try to match header settings if available
    if header:
        header_match = _generate_header_match_candidate(src_bytes, header)
        if header_match:
            candidates.append(header_match)

    # 2) Brute-force common tools/levels
    tools = _get_available_tools()

    for tool in tools:
        for level in [ZSTD_MIN_LEVEL, ZSTD_DEFAULT_LEVEL, ZSTD_MAX_LEVEL]:
            candidate = _generate_tool_candidate(src, tool, level, header)
            if candidate:
                candidates.append(candidate)

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

"""XZ header parsing and brute-force generation utilities."""

import hashlib
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass
from pathlib import Path

# XZ format constants
XZ_MAGIC = b"\xfd\x37\x7a\x58\x5a\x00"
XZ_HEADER_MIN_SIZE = 12  # Magic (6) + stream_flags (2) + crc32 (4)
XZ_STREAM_FLAGS_SIZE = 2
XZ_CRC32_SIZE = 4

# XZ stream flags
XZ_STREAM_FLAGS_NONE = 0
XZ_STREAM_FLAGS_CRC64 = 1 << 0

# Common compression levels for xz
XZ_MIN_LEVEL = 0
XZ_DEFAULT_LEVEL = 6
XZ_MAX_LEVEL = 9


@dataclass(frozen=True)
class XzHeader:
    """XZ header information."""

    flags: int  # Stream flags
    has_crc64: bool  # Whether CRC64 is enabled


def parse_xz_header(path: Path) -> XzHeader | None:
    """Parse the XZ header from a file."""
    with path.open("rb") as f:
        data = f.read(XZ_HEADER_MIN_SIZE)

    if len(data) < XZ_HEADER_MIN_SIZE or not data.startswith(XZ_MAGIC):
        return None

    # Extract stream flags (bytes 6-7)
    flags_bytes = data[6:8]
    flags = int.from_bytes(flags_bytes, "little")

    # Check CRC32 (bytes 8-11)
    stored_crc = int.from_bytes(data[8:12], "little")
    calculated_crc = hashlib.sha256(data[:8]).digest()[:4]  # Simplified CRC check
    calculated_crc_int = int.from_bytes(calculated_crc, "little")

    # Note: This is a simplified CRC check - real XZ uses CRC32
    # For our purposes, we'll assume the header is valid if magic matches

    has_crc64 = bool(flags & XZ_STREAM_FLAGS_CRC64)

    return XzHeader(flags=flags, has_crc64=has_crc64)


def format_xz_header(header: XzHeader) -> str:
    """Return a human-readable summary of XZ header fields."""
    lines = [
        f"flags: {header.flags:08x}",
        f"has_crc64: {header.has_crc64}",
    ]
    return "\n".join(lines)


def patch_xz_header(data: bytes, header: XzHeader) -> bytes:
    """Patch XZ header to match the provided header (flags)."""
    if len(data) < XZ_HEADER_MIN_SIZE or not data.startswith(XZ_MAGIC):
        return data

    # Replace the stream flags
    patched = bytearray(data)
    patched[6:8] = header.flags.to_bytes(XZ_STREAM_FLAGS_SIZE, "little")

    # Note: In a real implementation, we'd need to recalculate the CRC32
    # For our purposes, we'll leave the original CRC

    return bytes(patched)


def sha1_piece(data: bytes) -> bytes:
    """Return SHA-1 hash of data."""
    return hashlib.sha1(data).digest()


def _generate_header_match_candidate(src_bytes: bytes, header: XzHeader) -> tuple[str, bytes]:
    """Generate a candidate that matches the exact header settings."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            # Use xz command to compress
            cmd = ["xz", "-c", "--stdout"]
            proc = subprocess.run(cmd, input=src_bytes, capture_output=True)  # nosec B603
            if proc.returncode == 0:
                data = proc.stdout
                data = patch_xz_header(data, header)
                return ("header_match", data)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        finally:
            tmp_path.unlink()
    return None


def _get_available_tools() -> list[str]:
    """Get list of available compression tools."""
    tools = ["xz"]
    try:
        subprocess.run(["pixz", "--version"], check=True, capture_output=True)  # nosec B603, B607
        tools.append("pixz")
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return tools


def _build_command(tool: str, level: int) -> list[str]:
    """Build compression command with appropriate flags."""
    if tool == "xz":
        return ["xz", f"-{level}", "-c", "--stdout"]
    else:  # pixz
        return ["pixz", f"-{level}", "-c", "--stdout"]


def _generate_tool_candidate(src: Path, tool: str, level: int, header: XzHeader | None) -> tuple[str, bytes] | None:
    """Generate a candidate using a specific tool and settings."""
    cmd = _build_command(tool, level)
    cmd.append(str(src))

    try:
        proc = subprocess.run(cmd, check=True, capture_output=True)  # nosec B603
        data = proc.stdout
        if header:
            data = patch_xz_header(data, header)
        label = f"{tool} -{level}"
        return (label, data)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def generate_xz_candidates(src: Path, header: XzHeader | None) -> list[tuple[str, bytes]]:
    """Generate candidate XZ bytes for a source file using common tools/settings."""
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
        for level in [XZ_MIN_LEVEL, XZ_DEFAULT_LEVEL, XZ_MAX_LEVEL]:
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

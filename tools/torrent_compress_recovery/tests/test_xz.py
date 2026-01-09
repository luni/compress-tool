"""Tests for XZ header parsing, patching, and candidate generation."""

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from torrent_compress_recovery.xz import (
    XzHeader,
    find_matching_candidate,
    format_xz_header,
    generate_xz_candidates,
    parse_xz_header,
    patch_xz_header,
    sha1_piece,
    sha256_piece,
)


def test_parse_xz_header(temp_dir: Path):
    """Test parsing XZ header from a file."""
    # Create a simple XZ file using subprocess if xz is available
    if not shutil.which("xz"):
        pytest.skip("xz tool not available")

    raw = temp_dir / "raw"
    raw.mkdir()
    src = raw / "test.txt"
    src.write_text("hello world")
    xz_path = temp_dir / "test.txt.xz"

    # Create XZ file
    result = subprocess.run(["xz", "-c", str(src)], capture_output=True, check=True)
    xz_path.write_bytes(result.stdout)

    header = parse_xz_header(xz_path)
    assert header is not None
    assert isinstance(header.flags, int)
    assert isinstance(header.has_crc64, bool)


def test_format_xz_header():
    """Test formatting XZ header for display."""
    header = XzHeader(flags=0, has_crc64=False)
    out = format_xz_header(header)
    assert "flags: 0" in out
    assert "has_crc64: False" in out


def test_patch_xz_header(temp_dir: Path):
    """Test patching XZ header."""
    # Create minimal XZ-like data
    xz_magic = b"\xfd\x37\x7a\x58\x5a\x00"  # XZ magic
    stream_flags = b"\x00\x00"  # Simple flags
    crc_placeholder = b"\x00\x00\x00\x00"  # CRC32 placeholder
    data = xz_magic + stream_flags + crc_placeholder + b"some compressed data"

    # Create new header
    new_header = XzHeader(flags=1, has_crc64=True)
    patched = patch_xz_header(data, new_header)

    # Check that stream flags were updated
    assert patched[6:8] == new_header.flags.to_bytes(2, "little")


def test_generate_xz_candidates(temp_dir: Path):
    """Test generating XZ compression candidates."""
    if not shutil.which("xz") and not shutil.which("pixz"):
        pytest.skip("Neither xz nor pixz available")

    raw = temp_dir / "raw"
    raw.mkdir()
    src = raw / "sample.txt"
    src.write_text("sample content")

    header = XzHeader(flags=0, has_crc64=False)
    candidates = generate_xz_candidates(src, header)

    # Should have at least some candidates
    assert len(candidates) > 0

    # Check that candidates have labels and data
    for label, data in candidates:
        assert isinstance(label, str)
        assert isinstance(data, bytes)
        assert len(data) > 0


def test_sha1_piece():
    """Test SHA1 piece hashing."""
    data = b"hello"
    expected = hashlib.sha1(data).digest()
    assert sha1_piece(data) == expected


def test_sha256_piece():
    """Test SHA256 piece hashing."""
    data = b"world"
    expected = hashlib.sha256(data).digest()
    assert sha256_piece(data) == expected


def test_find_matching_candidate():
    """Test finding matching candidate by hash."""
    candidates = [
        ("a", b"foo"),
        ("b", b"bar"),
        ("c", b"baz"),
    ]
    target_hash = sha1_piece(b"bar")
    match = find_matching_candidate(candidates, target_hash, piece_length=3, hash_algo="sha1")
    assert match is not None
    assert match[0] == "b"
    assert match[1] == b"bar"

    # No match
    wrong_hash = sha1_piece(b"qux")
    assert find_matching_candidate(candidates, wrong_hash, piece_length=3, hash_algo="sha1") is None


def test_find_matching_candidate_sha256():
    """Test finding matching candidate by SHA256 hash."""
    candidates = [
        ("a", b"foo"),
        ("b", b"bar"),
        ("c", b"baz"),
    ]
    target_hash = sha256_piece(b"bar")
    match = find_matching_candidate(candidates, target_hash, piece_length=3, hash_algo="sha256")
    assert match is not None
    assert match[0] == "b"
    assert match[1] == b"bar"


def test_parse_xz_header_invalid_file(temp_dir: Path):
    """Test parsing header from invalid XZ file."""
    invalid_file = temp_dir / "invalid.xz"
    invalid_file.write_bytes(b"not an xz file")

    header = parse_xz_header(invalid_file)
    assert header is None


def test_parse_xz_header_too_small(temp_dir: Path):
    """Test parsing header from file that's too small."""
    small_file = temp_dir / "small.xz"
    small_file.write_bytes(b"\xfd\x37")  # Only partial magic

    header = parse_xz_header(small_file)
    assert header is None

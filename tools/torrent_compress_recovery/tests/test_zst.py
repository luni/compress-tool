"""Tests for Zstandard header parsing, patching, and candidate generation."""

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from torrent_compress_recovery.zst import (
    ZstdHeader,
    find_matching_candidate,
    format_zstd_header,
    generate_zstd_candidates,
    parse_zstd_header,
    patch_zstd_header,
    sha1_piece,
    sha256_piece,
)


def test_parse_zstd_header(temp_dir: Path):
    """Test parsing Zstandard header from a file."""
    # Create a simple Zstd file using subprocess if zstd is available
    if not shutil.which("zstd"):
        pytest.skip("zstd tool not available")

    raw = temp_dir / "raw"
    raw.mkdir()
    src = raw / "test.txt"
    src.write_text("hello world")
    zst_path = temp_dir / "test.txt.zst"

    # Create Zstd file
    result = subprocess.run(["zstd", "-c", str(src)], capture_output=True, check=True)
    zst_path.write_bytes(result.stdout)

    header = parse_zstd_header(zst_path)
    assert header is not None
    assert isinstance(header.window_log, int)
    assert isinstance(header.single_segment, bool)
    assert isinstance(header.has_checksum, bool)
    assert isinstance(header.has_dict_id, bool)


def test_format_zstd_header():
    """Test formatting Zstd header for display."""
    header = ZstdHeader(window_log=10, single_segment=False, has_checksum=True, has_dict_id=False)
    out = format_zstd_header(header)
    assert "window_log: 10" in out
    assert "single_segment: False" in out
    assert "has_checksum: True" in out
    assert "has_dict_id: False" in out


def test_patch_zstd_header(temp_dir: Path):
    """Test patching Zstd header."""
    # Create minimal Zstd-like data
    zstd_magic = b"\x28\xb5\x2f\xfd"  # Zstd magic
    frame_header = b"\x00\x00"  # Simple frame header
    data = zstd_magic + frame_header + b"some compressed data"

    # Create new header with window_log 11 (which is 0x0B in hex)
    new_header = ZstdHeader(window_log=11, single_segment=True, has_checksum=False, has_dict_id=True)
    patched = patch_zstd_header(data, new_header)

    # Check that frame header was updated - window_log should be in the lower 4 bits
    # The single_segment flag (0x20) should also be set
    expected_frame_header = (11 & 0x0F) | 0x20  # window_log + single_segment flag
    assert patched[4:6] == expected_frame_header.to_bytes(2, "little")


def test_generate_zstd_candidates(temp_dir: Path):
    """Test generating Zstd compression candidates."""
    if not shutil.which("zstd") and not shutil.which("pzstd"):
        pytest.skip("Neither zstd nor pzstd available")

    raw = temp_dir / "raw"
    raw.mkdir()
    src = raw / "sample.txt"
    src.write_text("sample content")

    header = ZstdHeader(window_log=10, single_segment=False, has_checksum=True, has_dict_id=False)
    candidates = generate_zstd_candidates(src, header)

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


def test_parse_zstd_header_invalid_file(temp_dir: Path):
    """Test parsing header from invalid Zstd file."""
    invalid_file = temp_dir / "invalid.zst"
    invalid_file.write_bytes(b"not a zstd file")

    header = parse_zstd_header(invalid_file)
    assert header is None


def test_parse_zstd_header_too_small(temp_dir: Path):
    """Test parsing header from file that's too small."""
    small_file = temp_dir / "small.zst"
    small_file.write_bytes(b"\x28\xb5")  # Only partial magic

    header = parse_zstd_header(small_file)
    assert header is None


def test_zstd_header_flags_parsing():
    """Test parsing different Zstd header flags."""
    # Test various flag combinations
    header = ZstdHeader(window_log=15, single_segment=True, has_checksum=True, has_dict_id=False)
    assert header.window_log == 15
    assert header.single_segment is True
    assert header.has_checksum is True
    assert header.has_dict_id is False

    formatted = format_zstd_header(header)
    assert "window_log: 15" in formatted
    assert "single_segment: True" in formatted
    assert "has_checksum: True" in formatted
    assert "has_dict_id: False" in formatted

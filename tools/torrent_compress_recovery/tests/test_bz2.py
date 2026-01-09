"""Bzip2 header parsing and brute-force generation utilities tests."""

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from torrent_compress_recovery.bz2 import (
    BZIP2_MAGIC,
    BZIP2_MAX_LEVEL,
    BZIP2_MIN_LEVEL,
    Bzip2Header,
    _get_block_size_description,
    format_bzip2_header,
    parse_bzip2_header,
    patch_bzip2_header,
    sha1_piece,
)


def test_parse_bzip2_header(temp_dir: Path):
    """Test parsing bzip2 header from a file."""
    if not shutil.which("bzip2"):
        pytest.skip("bzip2 tool not available")

    # Create test file
    bz2_file = temp_dir / "test.txt.bz2"
    result = subprocess.run(["bzip2", "-c"], input=b"Hello world", capture_output=True, check=True)
    bz2_file.write_bytes(result.stdout)

    header = parse_bzip2_header(bz2_file)
    assert header is not None
    assert isinstance(header.level, int)
    assert isinstance(header.block_size, int)
    assert BZIP2_MIN_LEVEL <= header.level <= BZIP2_MAX_LEVEL


def test_format_bzip2_header():
    """Test formatting bzip2 header for display."""
    header = Bzip2Header(level=6, block_size=600000)
    out = format_bzip2_header(header)
    assert "compression level: 6" in out
    assert "block size: 600,000 bytes (600 KB)" in out

    # Test different levels
    header_level1 = Bzip2Header(level=1, block_size=100000)
    out_level1 = format_bzip2_header(header_level1)
    assert "compression level: 1" in out_level1
    assert "block size: 100,000 bytes (100 KB)" in out_level1

    header_level9 = Bzip2Header(level=9, block_size=900000)
    out_level9 = format_bzip2_header(header_level9)
    assert "compression level: 9" in out_level9
    assert "block size: 900,000 bytes (900 KB)" in out_level9


def test_patch_bzip2_header(temp_dir: Path):
    """Test patching bzip2 header."""
    # Create minimal bzip2-like data
    bz2_magic = b"BZh"
    level_byte = b"1"  # Level 1
    data = bz2_magic + level_byte + b"some compressed data"

    # Create new header with level 9
    new_header = Bzip2Header(level=9, block_size=900000)
    patched = patch_bzip2_header(data, new_header)

    # Check that compression level was updated
    assert patched[3:4] == b"9"  # Level should be 9
    assert patched.startswith(BZIP2_MAGIC)


def test_generate_bzip2_candidates(temp_dir: Path):
    """Test generating bzip2 compression candidates."""
    if not shutil.which("bzip2"):
        pytest.skip("bzip2 tool not available")

    raw = temp_dir / "raw"
    raw.mkdir()
    src = raw / "sample.txt"
    src.write_text("sample content")

    header = Bzip2Header(level=6, block_size=600000)

    # Import here to avoid circular imports if the module doesn't exist
    try:
        from torrent_compress_recovery.bz2 import generate_bzip2_candidates

        candidates = generate_bzip2_candidates(src, header)

        # Should have at least some candidates
        assert len(candidates) > 0

        # Check that candidates have labels and data
        for label, data in candidates:
            assert isinstance(label, str)
            assert isinstance(data, bytes)
            assert len(data) > 0
    except ImportError:
        pytest.skip("generate_bzip2_candidates not available")


def test_sha1_piece():
    """Test SHA-1 piece hashing."""
    data = b"test data for sha1"
    hash_result = sha1_piece(data)

    # Verify it's a 20-byte SHA-1 hash
    assert isinstance(hash_result, bytes)
    assert len(hash_result) == 20

    # Verify consistency
    hash_result2 = sha1_piece(data)
    assert hash_result == hash_result2


def test_sha256_piece():
    """Test SHA-256 piece hashing."""
    data = b"test data for sha256"

    # Import here to avoid circular imports if the function doesn't exist
    try:
        from torrent_compress_recovery.bz2 import sha256_piece

        hash_result = sha256_piece(data)

        # Verify it's a 32-byte SHA-256 hash
        assert isinstance(hash_result, bytes)
        assert len(hash_result) == 32

        # Verify consistency
        hash_result2 = sha256_piece(data)
        assert hash_result == hash_result2
    except ImportError:
        pytest.skip("sha256_piece not available")


def test_find_matching_candidate():
    """Test finding matching candidate for bzip2 data."""
    data = b"test data for matching"
    hash_result = hashlib.sha1(data).digest()

    # Import here to avoid circular imports if the function doesn't exist
    try:
        from torrent_compress_recovery.bz2 import find_matching_candidate as find_bzip2_candidate

        # Test with matching candidate
        candidates = [("test_candidate", data)]
        result = find_bzip2_candidate(candidates, hash_result, piece_length=len(data))
        assert result == ("test_candidate", data)

        # Test with no matching candidate
        candidates = [("wrong_candidate", b"wrong data")]
        result = find_bzip2_candidate(candidates, hash_result, piece_length=len(data))
        assert result is None
    except ImportError:
        pytest.skip("find_matching_candidate not available")


def test_find_matching_candidate_sha256():
    """Test finding matching candidate for bzip2 data using SHA-256."""
    data = b"test data for sha256 matching"
    hash_result = hashlib.sha256(data).digest()

    # Import here to avoid circular imports if the function doesn't exist
    try:
        from torrent_compress_recovery.bz2 import find_matching_candidate_sha256

        # Test with matching candidate
        candidates = [("test_candidate", data)]
        result = find_matching_candidate_sha256(candidates, hash_result)
        assert result == data

        # Test with no matching candidate
        candidates = [("wrong_candidate", b"wrong data")]
        result = find_matching_candidate_sha256(candidates, hash_result)
        assert result is None
    except ImportError:
        pytest.skip("find_matching_candidate_sha256 not available")


def test_parse_bzip2_header_invalid_file(temp_dir: Path):
    """Test parsing header from invalid bzip2 file."""
    invalid_file = temp_dir / "invalid.bz2"
    invalid_file.write_bytes(b"not a bzip2 file")

    header = parse_bzip2_header(invalid_file)
    assert header is None


def test_parse_bzip2_header_too_small(temp_dir: Path):
    """Test parsing header from file that's too small."""
    small_file = temp_dir / "small.bz2"
    small_file.write_bytes(b"BZ")  # Only partial magic

    header = parse_bzip2_header(small_file)
    assert header is None


def test_parse_bzip2_header_invalid_level(temp_dir: Path):
    """Test parsing header with invalid compression level."""
    # Create bzip2-like data with invalid level (not 1-9)
    bz2_magic = b"BZh"
    invalid_level = b"0"  # Invalid level
    data = bz2_magic + invalid_level + b"some compressed data"

    invalid_file = temp_dir / "invalid_level.bz2"
    invalid_file.write_bytes(data)

    header = parse_bzip2_header(invalid_file)
    assert header is None


def test_bzip2_header_usage_in_compression():
    """Test that header information is actually used in compression."""
    # Create minimal bzip2-like data
    bz2_magic = b"BZh"
    level_byte = b"1"  # Level 1
    data = bz2_magic + level_byte + b"some compressed data"

    # Test different header settings produce different results
    header1 = Bzip2Header(level=1, block_size=100000)
    header2 = Bzip2Header(level=9, block_size=900000)

    patched1 = patch_bzip2_header(data, header1)
    patched2 = patch_bzip2_header(data, header2)

    # Results should be different
    assert patched1 != patched2
    assert patched1[3:4] == b"1"  # Level 1
    assert patched2[3:4] == b"9"  # Level 9


def test_get_block_size_description():
    """Test block size description function."""
    # Test valid levels
    assert _get_block_size_description(1) == "100,000 bytes (100 KB)"
    assert _get_block_size_description(6) == "600,000 bytes (600 KB)"
    assert _get_block_size_description(9) == "900,000 bytes (900 KB)"

    # Test invalid level (should return 0)
    assert _get_block_size_description(0) == "0 bytes (0 KB)"
    assert _get_block_size_description(10) == "0 bytes (0 KB)"

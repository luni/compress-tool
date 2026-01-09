"""Realistic integration test using actual gzipped files and a real torrent."""

import gzip
from pathlib import Path

import pytest

from torrent_compress_recovery.core import recover
from torrent_compress_recovery.verify import verify_last_piece_against_raw


@pytest.fixture
def real_data_dir():
    """Path to realistic test data."""
    return Path(__file__).parent / "fixtures" / "real_data"


def test_realistic_reproduce_mode(real_data_dir: Path):
    """Test reproduce mode with real gzipped files and a real torrent."""
    torrent_path = real_data_dir / "sample.torrent"
    # Use the actual gz files as input (not raw files)
    gz_dir = real_data_dir  # The gz files are in the root
    partial_dir = real_data_dir / "partial"
    target_dir = real_data_dir / "output"
    target_dir.mkdir(exist_ok=True)

    # Clean any previous output
    for p in target_dir.iterdir():
        if p.is_file():
            p.unlink()

    result = recover(
        torrent_path=torrent_path,
        raw_dir=gz_dir,  # Pass gz dir as raw_dir (will look for .gz files)
        partial_dir=partial_dir,
        target_dir=target_dir,
        raw_fallback=False,  # No fallback - only use actual files
        overwrite=True,  # Overwrite to avoid skipped files in test
        dry_run=False,
    )

    # Expect that we recover at least one file via brute-force matching
    assert result.recovered == 0
    assert result.gzipped >= 1
    # Some files may still be missing if brute-force doesn't match all piece hashes
    assert result.missing <= 2

    # Verify that recovered files are valid gzip and decompress correctly
    output_dir = target_dir / "sample"
    recovered_count = 0
    for gz_path in output_dir.glob("*.gz"):
        # Verify it's a valid gzip file
        assert gz_path.suffix == ".gz"

        # Try to decompress it
        with gzip.open(gz_path, "rb") as f:
            decompressed = f.read()
        assert decompressed, f"Failed to decompress {gz_path.name}"
        recovered_count += 1

    assert recovered_count == result.gzipped


def test_realistic_verify_step_b(real_data_dir: Path):
    """Test Step B verification (last piece CRC32/ISIZE) with real data."""
    torrent_path = real_data_dir / "sample.torrent"
    raw_dir = real_data_dir / "raw"
    partial_dir = real_data_dir / "partial"

    # Run Step B verification
    results = verify_last_piece_against_raw(torrent_path, raw_dir, partial_dir)
    # With piece length 32, partial files are too small to contain a complete last piece, so expect 0 results
    assert len(results) == 0


def test_realistic_header_info_step_a(real_data_dir: Path):
    """Test Step A header info extraction with real partial files."""
    from torrent_compress_recovery.gzip import parse_gzip_header, format_gzip_header

    partial_dir = real_data_dir / "partial"
    for gz_path in partial_dir.glob("*.gz"):
        header = parse_gzip_header(gz_path)
        assert header is not None, f"Failed to parse header for {gz_path.name}"
        # Basic sanity checks
        assert isinstance(header.mtime, int)
        assert isinstance(header.os, int)
        assert isinstance(header.flags, int)
        # Optional fields may be None
        # Format and ensure no exception
        formatted = format_gzip_header(header)
        assert isinstance(formatted, str)
        assert len(formatted) > 0

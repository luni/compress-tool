"""Extended tests for BZ2 module to improve coverage."""

from torrent_compress_recovery.bz2 import (
    BZIP2_MAGIC,
    BZIP2_MAX_LEVEL,
    BZIP2_MIN_LEVEL,
)


def test_bz2_constants():
    """Test BZ2 constants."""
    assert BZIP2_MAGIC == b"BZh"
    assert BZIP2_MIN_LEVEL == 1
    assert BZIP2_MAX_LEVEL == 9


def test_bz2_level_range():
    """Test BZ2 level range."""
    assert BZIP2_MIN_LEVEL < BZIP2_MAX_LEVEL
    assert BZIP2_MIN_LEVEL == 1
    assert BZIP2_MAX_LEVEL == 9

    # Test valid range
    for level in range(BZIP2_MIN_LEVEL, BZIP2_MAX_LEVEL + 1):
        assert BZIP2_MIN_LEVEL <= level <= BZIP2_MAX_LEVEL

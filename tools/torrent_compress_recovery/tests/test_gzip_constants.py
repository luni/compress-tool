"""Extended tests for gzip module constants to improve coverage."""

from torrent_compress_recovery.gzip import (
    GZIP_FLAG_FCOMMENT,
    GZIP_FLAG_FEXTRA,
    GZIP_FLAG_FHCRC,
    GZIP_FLAG_FNAME,
    GZIP_FLAG_FTEXT,
    GZIP_MAGIC,
    GZIP_METHOD_DEFLATE,
    GZIP_MIN_HEADER_SIZE,
)


def test_gzip_constants():
    """Test gzip module constants."""
    assert GZIP_MAGIC == b"\x1f\x8b"
    assert GZIP_METHOD_DEFLATE == 8
    assert GZIP_MIN_HEADER_SIZE == 10
    assert GZIP_FLAG_FTEXT == 1
    assert GZIP_FLAG_FHCRC == 2
    assert GZIP_FLAG_FEXTRA == 4
    assert GZIP_FLAG_FNAME == 8
    assert GZIP_FLAG_FCOMMENT == 16


def test_gzip_flag_values():
    """Test that gzip flags are powers of 2."""
    flags = [
        GZIP_FLAG_FTEXT,
        GZIP_FLAG_FHCRC,
        GZIP_FLAG_FEXTRA,
        GZIP_FLAG_FNAME,
        GZIP_FLAG_FCOMMENT,
    ]

    # Each flag should be a power of 2
    for flag in flags:
        assert flag & (flag - 1) == 0  # Power of 2 check

    # All flags should be unique
    assert len(flags) == len(set(flags))


def test_gzip_magic_bytes():
    """Test gzip magic bytes."""
    assert len(GZIP_MAGIC) == 2
    assert GZIP_MAGIC[0] == 0x1F
    assert GZIP_MAGIC[1] == 0x8B

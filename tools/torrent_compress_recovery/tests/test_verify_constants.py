"""Extended tests for verify module constants to improve coverage."""

from torrent_compress_recovery.verify import (
    GZIP_TRAILER_SIZE,
    XZ_FOOTER_SIZE,
    ZSTD_FRAME_FOOTER_SIZE,
)


def test_verify_constants():
    """Test verify module constants."""
    assert GZIP_TRAILER_SIZE == 8
    assert XZ_FOOTER_SIZE == 12
    assert ZSTD_FRAME_FOOTER_SIZE == 4


def test_footer_sizes():
    """Test that footer sizes are reasonable."""
    # All footer sizes should be positive
    assert GZIP_TRAILER_SIZE > 0
    assert XZ_FOOTER_SIZE > 0
    assert ZSTD_FRAME_FOOTER_SIZE > 0

    # XZ should be larger than GZIP (more complex format)
    assert XZ_FOOTER_SIZE > GZIP_TRAILER_SIZE

    # ZSTD should be smaller (minimal footer)
    assert ZSTD_FRAME_FOOTER_SIZE < GZIP_TRAILER_SIZE

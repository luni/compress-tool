"""Extended tests for ZSTD module to improve coverage."""

from torrent_compress_recovery.zst import (
    ZSTD_FRAME_HEADER_CHECKSUM_FLAG,
    ZSTD_FRAME_HEADER_DICT_ID_FLAG,
    ZSTD_FRAME_HEADER_RESERVED_FLAG,
    ZSTD_FRAME_HEADER_SINGLE_SEGMENT_FLAG,
    ZSTD_FRAME_HEADER_WINDOWLOG_MASK,
)


def test_zstd_frame_header_constants():
    """Test ZSTD frame header constants."""
    assert ZSTD_FRAME_HEADER_WINDOWLOG_MASK == 0x0F
    assert ZSTD_FRAME_HEADER_SINGLE_SEGMENT_FLAG == 0x20
    assert ZSTD_FRAME_HEADER_CHECKSUM_FLAG == 0x10
    assert ZSTD_FRAME_HEADER_DICT_ID_FLAG == 0x08
    assert ZSTD_FRAME_HEADER_RESERVED_FLAG == 0x02


def test_zstd_frame_header_flag_values():
    """Test that frame header flags have expected values."""
    # Verify the constants are powers of 2 (bit flags)
    flags = [
        ZSTD_FRAME_HEADER_WINDOWLOG_MASK,
        ZSTD_FRAME_HEADER_SINGLE_SEGMENT_FLAG,
        ZSTD_FRAME_HEADER_CHECKSUM_FLAG,
        ZSTD_FRAME_HEADER_DICT_ID_FLAG,
        ZSTD_FRAME_HEADER_RESERVED_FLAG,
    ]

    # Each flag should be a power of 2 (except the mask)
    for flag in flags:
        if flag != ZSTD_FRAME_HEADER_WINDOWLOG_MASK:
            assert flag & (flag - 1) == 0  # Power of 2 check

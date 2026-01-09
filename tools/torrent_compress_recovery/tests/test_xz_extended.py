"""Extended tests for XZ module to improve coverage."""

from torrent_compress_recovery.xz import (
    XZ_CHECK_CRC32,
    XZ_CHECK_CRC64,
    XZ_CHECK_NONE,
    XZ_CHECK_SHA256,
)


def test_xz_check_constants():
    """Test XZ check type constants."""
    assert XZ_CHECK_NONE == 0x00
    assert XZ_CHECK_CRC32 == 0x01
    assert XZ_CHECK_CRC64 == 0x04
    assert XZ_CHECK_SHA256 == 0x0A


def test_xz_check_values():
    """Test that check constants have expected values."""
    # Verify the constants are unique
    check_values = [XZ_CHECK_NONE, XZ_CHECK_CRC32, XZ_CHECK_CRC64, XZ_CHECK_SHA256]
    assert len(check_values) == len(set(check_values))

    # Verify they are in reasonable range
    for check in check_values:
        assert 0x00 <= check <= 0xFF

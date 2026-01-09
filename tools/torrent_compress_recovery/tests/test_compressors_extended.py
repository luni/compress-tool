"""Extended tests for compressors module to improve coverage."""

from pathlib import Path

import pytest

from torrent_compress_recovery.compressors import (
    get_compressor,
    register_compressor,
)


def test_register_compressor():
    """Test registering a custom compressor."""
    from torrent_compress_recovery.compressors import Compressor

    class TestCompressor(Compressor):
        @property
        def extension(self) -> str:
            return ".test"

        def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(src.read_text() + " compressed")

    # Register the compressor
    register_compressor(".test", TestCompressor)

    # Test that it's registered
    compressor = get_compressor(".test")
    assert isinstance(compressor, TestCompressor)
    assert compressor.extension == ".test"


def test_get_compressor_unknown():
    """Test getting compressor for unknown extension."""
    with pytest.raises(ValueError, match=r"No compressor registered for extension \.unknown"):
        get_compressor(".unknown")


def test_get_compressor_case_sensitive():
    """Test that compressor lookup is case sensitive."""
    # Should work with lowercase
    compressor = get_compressor(".gz")
    assert compressor is not None

    # Should not work with uppercase (case sensitive)
    with pytest.raises(ValueError, match=r"No compressor registered for extension \.GZ"):
        get_compressor(".GZ")


def test_get_compressor_existing():
    """Test getting existing compressors."""
    # Test all existing compressors
    gz_compressor = get_compressor(".gz")
    assert gz_compressor is not None
    assert gz_compressor.extension == ".gz"

    bz2_compressor = get_compressor(".bz2")
    assert bz2_compressor is not None
    assert bz2_compressor.extension == ".bz2"

    xz_compressor = get_compressor(".xz")
    assert xz_compressor is not None
    assert xz_compressor.extension == ".xz"

    zst_compressor = get_compressor(".zst")
    assert zst_compressor is not None
    assert zst_compressor.extension == ".zst"


def test_register_compressor_override():
    """Test that registering a compressor overrides existing one."""
    from torrent_compress_recovery.compressors import Compressor

    class OverrideCompressor(Compressor):
        @property
        def extension(self) -> str:
            return ".override"

        def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
            pass

    # Register the compressor
    register_compressor(".override", OverrideCompressor)

    # Test that it's registered
    compressor = get_compressor(".override")
    assert isinstance(compressor, OverrideCompressor)

    # Override with another compressor
    class NewOverrideCompressor(Compressor):
        @property
        def extension(self) -> str:
            return ".override"

        def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
            pass

    # Register the new compressor (should override)
    register_compressor(".override", NewOverrideCompressor)

    # Test that the new one is registered
    new_compressor = get_compressor(".override")
    assert isinstance(new_compressor, NewOverrideCompressor)

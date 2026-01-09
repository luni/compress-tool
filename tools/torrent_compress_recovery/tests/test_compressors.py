"""Test compressor implementations."""

import gzip
from pathlib import Path

import pytest

from torrent_compress_recovery.compressors import (
    Bzip2Compressor,
    Compressor,
    GzipCompressor,
    XzCompressor,
    ZstdCompressor,
    get_compressor,
    register_compressor,
)


class TestCompressor:
    """Test the base Compressor class."""

    def test_compressor_is_abstract(self):
        """Test that Compressor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Compressor()


class TestGzipCompressor:
    """Test GzipCompressor implementation."""

    def test_extension_property(self):
        """Test that extension property returns correct value."""
        compressor = GzipCompressor()
        assert compressor.extension == ".gz"

    def test_compress_dry_run(self, tmp_path: Path):
        """Test compress method in dry run mode."""
        compressor = GzipCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "test.txt.gz"

        src.write_text("test content")

        # Dry run should not create any files
        compressor.compress(src, dst, dry_run=True)

        assert not dst.exists()

    def test_compress_actual(self, tmp_path: Path):
        """Test actual compression."""
        compressor = GzipCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "subdir" / "test.txt.gz"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()
        assert dst.parent.exists()

        # Verify the compressed content
        with gzip.open(dst, "rt") as f:
            assert f.read() == "test content"

    def test_compress_creates_parent_directories(self, tmp_path: Path):
        """Test that compress creates parent directories."""
        compressor = GzipCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "nested" / "deep" / "test.txt.gz"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()
        assert dst.parent.exists()
        assert dst.parent.parent.exists()

    def test_compress_with_binary_content(self, tmp_path: Path):
        """Test compression of binary content."""
        compressor = GzipCompressor()
        src = tmp_path / "test.bin"
        dst = tmp_path / "test.bin.gz"

        # Create binary data
        binary_data = bytes(range(256))
        src.write_bytes(binary_data)

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()

        # Verify the compressed content
        with gzip.open(dst, "rb") as f:
            assert f.read() == binary_data


class TestXzCompressor:
    """Test XzCompressor implementation."""

    def test_extension_property(self):
        """Test that extension property returns correct value."""
        compressor = XzCompressor()
        assert compressor.extension == ".xz"

    def test_compress_dry_run(self, tmp_path: Path):
        """Test compress method in dry run mode."""
        compressor = XzCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "test.txt.xz"

        src.write_text("test content")

        # Dry run should not create any files
        compressor.compress(src, dst, dry_run=True)

        assert not dst.exists()

    def test_compress_actual(self, tmp_path: Path):
        """Test actual compression if xz tool is available."""
        import shutil

        pytest.skip("xz tool not available") if not shutil.which("xz") else None

        compressor = XzCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "subdir" / "test.txt.xz"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()
        assert dst.parent.exists()

    def test_compress_creates_parent_directories(self, tmp_path: Path):
        """Test that compress creates parent directories."""
        import shutil

        pytest.skip("xz tool not available") if not shutil.which("xz") else None

        compressor = XzCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "nested" / "deep" / "test.txt.xz"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()
        assert dst.parent.exists()
        assert dst.parent.parent.exists()

    def test_compress_fallback_to_pixz(self, tmp_path: Path):
        """Test fallback to pixz when xz is not available."""
        import shutil

        pytest.skip("Neither xz nor pixz available") if not (shutil.which("xz") or shutil.which("pixz")) else None

        compressor = XzCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "test.txt.xz"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()

    def test_compress_no_tools_available(self, tmp_path: Path):
        """Test error when neither xz nor pixz is available."""
        import shutil

        if shutil.which("xz") or shutil.which("pixz"):
            pytest.skip("xz or pixz tool is available")

        compressor = XzCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "test.txt.xz"

        src.write_text("test content")

        with pytest.raises(RuntimeError, match="Neither xz nor pixz is available"):
            compressor.compress(src, dst, dry_run=False)


class TestZstdCompressor:
    """Test ZstdCompressor implementation."""

    def test_extension_property(self):
        """Test that extension property returns correct value."""
        compressor = ZstdCompressor()
        assert compressor.extension == ".zst"

    def test_compress_dry_run(self, tmp_path: Path):
        """Test compress method in dry run mode."""
        compressor = ZstdCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "test.txt.zst"

        src.write_text("test content")

        # Dry run should not create any files
        compressor.compress(src, dst, dry_run=True)

        assert not dst.exists()

    def test_compress_actual(self, tmp_path: Path):
        """Test actual compression if zstd tool is available."""
        import shutil

        pytest.skip("zstd tool not available") if not shutil.which("zstd") else None

        compressor = ZstdCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "subdir" / "test.txt.zst"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()
        assert dst.parent.exists()

    def test_compress_creates_parent_directories(self, tmp_path: Path):
        """Test that compress creates parent directories."""
        import shutil

        pytest.skip("zstd tool not available") if not shutil.which("zstd") else None

        compressor = ZstdCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "nested" / "deep" / "test.txt.zst"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()
        assert dst.parent.exists()
        assert dst.parent.parent.exists()

    def test_compress_fallback_to_pzstd(self, tmp_path: Path):
        """Test fallback to pzstd when zstd is not available."""
        import shutil

        pytest.skip("Neither zstd nor pzstd available") if not (shutil.which("zstd") or shutil.which("pzstd")) else None

        compressor = ZstdCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "test.txt.zst"

        src.write_text("test content")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()

    def test_compress_no_tools_available(self, tmp_path: Path):
        """Test error when neither zstd nor pzstd is available."""
        import shutil

        if shutil.which("zstd") or shutil.which("pzstd"):
            pytest.skip("zstd or pzstd tool is available")

        compressor = ZstdCompressor()
        src = tmp_path / "test.txt"
        dst = tmp_path / "test.txt.zst"

        src.write_text("test content")

        with pytest.raises(RuntimeError, match="Neither zstd nor pzstd is available"):
            compressor.compress(src, dst, dry_run=False)


class TestCompressorRegistry:
    """Test compressor registry functions."""

    def test_get_compressor_known_extension(self):
        """Test getting compressor for known extension."""
        compressor = get_compressor(".gz")
        assert isinstance(compressor, GzipCompressor)

        # Test new compressors
        xz_compressor = get_compressor(".xz")
        assert isinstance(xz_compressor, XzCompressor)

        zstd_compressor = get_compressor(".zst")
        assert isinstance(zstd_compressor, ZstdCompressor)

    def test_get_compressor_unknown_extension(self):
        """Test getting compressor for unknown extension raises error."""
        with pytest.raises(ValueError, match="No compressor registered for extension .unknown"):
            get_compressor(".unknown")

    def test_register_compressor(self):
        """Test registering a new compressor."""

        class TestCompressor(Compressor):
            @property
            def extension(self) -> str:
                return ".test"

            def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
                pass

        # Register the compressor
        register_compressor(".test", TestCompressor)

        # Should be able to get it now
        compressor = get_compressor(".test")
        assert isinstance(compressor, TestCompressor)

    def test_register_compressor_overwrites_existing(self):
        """Test that registering overwrites existing compressor."""

        class NewGzipCompressor(Compressor):
            @property
            def extension(self) -> str:
                return ".gz"

            def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
                pass

        # Register new compressor for .gz
        register_compressor(".gz", NewGzipCompressor)

        # Should get the new one
        compressor = get_compressor(".gz")
        assert isinstance(compressor, NewGzipCompressor)

    def test_register_compressor_invalid_class(self):
        """Test registering invalid compressor class."""

        class InvalidCompressor:
            """Not a subclass of Compressor."""

            pass

        # This should work at registration time but fail when trying to instantiate
        register_compressor(".invalid", InvalidCompressor)

        # Getting the compressor should work, but using it might fail
        # The registry doesn't validate the class at registration time
        compressor = get_compressor(".invalid")
        assert isinstance(compressor, InvalidCompressor)


class TestGzipCompressorEdgeCases:
    """Test edge cases for GzipCompressor."""

    def test_compress_empty_file(self, tmp_path: Path):
        """Test compressing an empty file."""
        compressor = GzipCompressor()
        src = tmp_path / "empty.txt"
        dst = tmp_path / "empty.txt.gz"

        src.write_text("")

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()

        # Verify the compressed content is empty
        with gzip.open(dst, "rt") as f:
            assert f.read() == ""

    def test_compress_large_file(self, tmp_path: Path):
        """Test compressing a large file."""
        compressor = GzipCompressor()
        src = tmp_path / "large.txt"
        dst = tmp_path / "large.txt.gz"

        # Create a 1MB file
        large_content = "x" * (1024 * 1024)
        src.write_text(large_content)

        compressor.compress(src, dst, dry_run=False)

        assert dst.exists()

        # Verify the compressed content
        with gzip.open(dst, "rt") as f:
            assert f.read() == large_content

    def test_compress_nonexistent_source(self, tmp_path: Path):
        """Test compressing a nonexistent source file."""
        compressor = GzipCompressor()
        src = tmp_path / "nonexistent.txt"
        dst = tmp_path / "nonexistent.txt.gz"

        # Should raise FileNotFoundError when trying to open nonexistent source
        with pytest.raises(FileNotFoundError):
            compressor.compress(src, dst, dry_run=False)

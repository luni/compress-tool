"""Compressor implementations for fallback from raw to compressed."""

import bz2
import gzip
import shutil
import subprocess  # nosec B404
from abc import ABC, abstractmethod
from pathlib import Path


class Compressor(ABC):
    """Base class for compressors."""

    @property
    @abstractmethod
    def extension(self) -> str:
        """File extension this compressor handles, e.g. '.gz'."""

    @abstractmethod
    def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
        """Compress src to dst. Parent dirs are created automatically."""


class GzipCompressor(Compressor):
    """gzip compressor."""

    @property
    def extension(self) -> str:
        return ".gz"

    def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
        if dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as f_in:
            with gzip.GzipFile(filename="", mode="wb", fileobj=dst.open("wb"), mtime=0) as gz:
                shutil.copyfileobj(f_in, gz)


class Bzip2Compressor(Compressor):
    """bzip2 compressor."""

    @property
    def extension(self) -> str:
        return ".bz2"

    def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
        if dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as f_in:
            with dst.open("wb") as f_out:
                f_out.write(bz2.compress(f_in.read()))


class XzCompressor(Compressor):
    """xz compressor."""

    @property
    def extension(self) -> str:
        return ".xz"

    def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
        if dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Try xz command first, then fallback to pixz
        for tool in ["xz", "pixz"]:
            try:
                cmd = [tool, "-c", str(src)]
                proc = subprocess.run(cmd, check=True, capture_output=True)  # nosec B603
                dst.write_bytes(proc.stdout)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue

        # If both tools fail, raise an error
        raise RuntimeError("Neither xz nor pixz is available")


class ZstdCompressor(Compressor):
    """zstd compressor."""

    @property
    def extension(self) -> str:
        return ".zst"

    def compress(self, src: Path, dst: Path, dry_run: bool) -> None:
        if dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Try zstd command first, then fallback to pzstd
        for tool in ["zstd", "pzstd"]:
            try:
                cmd = [tool, "-c", str(src)]
                proc = subprocess.run(cmd, check=True, capture_output=True)  # nosec B603
                dst.write_bytes(proc.stdout)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue

        # If both tools fail, raise an error
        raise RuntimeError("Neither zstd nor pzstd is available")


# Registry of compressors
_COMPRESSORS: dict[str, type[Compressor]] = {
    ".gz": GzipCompressor,
    ".bz2": Bzip2Compressor,
    ".xz": XzCompressor,
    ".zst": ZstdCompressor,
}


def get_compressor(ext: str) -> Compressor:
    """Return a Compressor instance for the given extension."""
    if ext not in _COMPRESSORS:
        raise ValueError(f"No compressor registered for extension {ext}")
    return _COMPRESSORS[ext]()


def register_compressor(ext: str, cls: type[Compressor]) -> None:
    """Register a new compressor for an extension."""
    _COMPRESSORS[ext] = cls

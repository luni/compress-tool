"""Compressor implementations for fallback from raw to compressed."""

import gzip
import shutil
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


# Registry of compressors
_COMPRESSORS: dict[str, type[Compressor]] = {
    ".gz": GzipCompressor,
}


def get_compressor(ext: str) -> Compressor:
    """Return a Compressor instance for the given extension."""
    if ext not in _COMPRESSORS:
        raise ValueError(f"No compressor registered for extension {ext}")
    return _COMPRESSORS[ext]()


def register_compressor(ext: str, cls: type[Compressor]) -> None:
    """Register a new compressor for an extension."""
    _COMPRESSORS[ext] = cls

"""pytest fixtures for torrent-compress-recovery tests."""

import gzip
import shutil
import tempfile
from pathlib import Path

import pytest


def make_simple_torrent(name: bytes, files: list[dict[str, int]], piece_length: int = 16384) -> bytes:
    """Create a minimal v1 torrent dict and return bencoded bytes."""
    # Compute concatenated file data and piece hashes
    concatenated = b""
    for f in files:
        # For testing, we don't have real file contents; use zero bytes
        concatenated += b"\x00" * f["length"]
    # Split into pieces and hash each
    pieces = b""
    for i in range(0, len(concatenated), piece_length):
        piece = concatenated[i : i + piece_length]
        import hashlib

        pieces += hashlib.sha1(piece).digest()
    info = {b"name": name, b"piece length": piece_length, b"pieces": pieces, b"files": []}
    for f in files:
        info[b"files"].append({b"length": f["length"], b"path": [p.encode() for p in f["path"]]})
    torrent = {b"info": info}

    # Simple bencode encoder (no need to import from module)
    def encode(obj):
        if isinstance(obj, int):
            return b"i" + str(obj).encode() + b"e"
        if isinstance(obj, bytes):
            return str(len(obj)).encode() + b":" + obj
        if isinstance(obj, str):
            return str(len(obj)).encode() + b":" + obj.encode()
        if isinstance(obj, list):
            return b"l" + b"".join(encode(x) for x in obj) + b"e"
        if isinstance(obj, dict):
            items = sorted(obj.items(), key=lambda kv: kv[0])
            return b"d" + b"".join(encode(k) + encode(v) for k, v in items) + b"e"
        raise TypeError(type(obj))

    return encode(torrent)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def raw_files(temp_dir):
    raw = temp_dir / "raw"
    raw.mkdir()
    files = {}
    for name, content in {
        "file1.txt": b"hello world",
        "file2.txt": b"another test file",
    }.items():
        p = raw / name
        p.write_bytes(content)
        files[name] = p
    return files


@pytest.fixture
def gz_files(temp_dir, raw_files):
    gz = temp_dir / "gz"
    gz.mkdir()
    gz_files = {}
    for name, src in raw_files.items():
        dst = gz / (name + ".gz")
        with src.open("rb") as f_in:
            with gzip.GzipFile(filename="", mode="wb", fileobj=dst.open("wb"), mtime=0) as f_out:
                shutil.copyfileobj(f_in, f_out)
        gz_files[name + ".gz"] = dst
    return gz_files


@pytest.fixture
def partial_gz_files(temp_dir, gz_files):
    partial = temp_dir / "partial"
    partial.mkdir()
    partial_files = {}
    for name, src in gz_files.items():
        dst = partial / name
        # Truncate to simulate partial download
        dst.write_bytes(src.read_bytes()[: src.stat().st_size // 2])
        partial_files[name] = dst
    return partial_files


@pytest.fixture
def sample_torrent(temp_dir, gz_files):
    torrent_path = temp_dir / "sample.torrent"
    # Build torrent file list from gz_files
    files = [{"path": [p.name], "length": p.stat().st_size} for p in gz_files.values()]
    torrent_path.write_bytes(make_simple_torrent(b"sample", files))
    return torrent_path

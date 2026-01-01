#!/usr/bin/env python3
import importlib.util
import re
import subprocess
from typing import Callable, Optional
import zipfile


def has_module(name: str) -> bool:
    spec = importlib.util.find_spec(name)
    return spec is not None


def unzip_supports_lzma() -> bool:
    """Return True if the system unzip understands LZMA compressed entries."""
    try:
        output = subprocess.check_output(
            ["unzip", "-v"], stderr=subprocess.STDOUT, text=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    match = re.search(r"UnZip\s+(\d+)\.(\d+)", output, flags=re.IGNORECASE)
    if not match:
        return False

    major, minor = int(match.group(1)), int(match.group(2))
    return (major, minor) >= (6, 3)


def compressor_supported(
    attr: str,
    module: Optional[str],
    extra: Optional[Callable[[], bool]] = None,
) -> bool:
    if not hasattr(zipfile, attr):
        return False
    if module and not has_module(module):
        return False
    if extra and not extra():
        return False
    return True


def main() -> None:
    candidates = [
        ("store", "ZIP_STORED", None, None),
        ("deflate", "ZIP_DEFLATED", "zlib", None),
        ("bzip2", "ZIP_BZIP2", "bz2", None),
        ("lzma", "ZIP_LZMA", "lzma", unzip_supports_lzma),
    ]

    supported = [
        name
        for name, attr, module, extra in candidates
        if compressor_supported(attr, module, extra)
    ]
    print("\n".join(supported))


if __name__ == "__main__":
    main()

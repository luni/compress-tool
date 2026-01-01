#!/usr/bin/env python3
import importlib.util
import sys
import zipfile


def has_module(name: str) -> bool:
    spec = importlib.util.find_spec(name)
    return spec is not None


def main() -> None:
    candidates = [
        ("store", "ZIP_STORED", None),
        ("deflate", "ZIP_DEFLATED", "zlib"),
        ("bzip2", "ZIP_BZIP2", "bz2"),
        ("lzma", "ZIP_LZMA", "lzma"),
    ]

    supported = []
    for name, attr, module in candidates:
        if not hasattr(zipfile, attr):
            continue
        if module and not has_module(module):
            continue
        supported.append(name)

    print("\n".join(supported))


if __name__ == "__main__":
    main()

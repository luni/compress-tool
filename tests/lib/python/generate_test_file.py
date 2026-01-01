#!/usr/bin/env python3
import sys
from pathlib import Path


def main(path_str: str, size_str: str, seed: str) -> None:
    path = Path(path_str)
    size = int(size_str)
    pattern = (seed + "\n").encode("utf-8")

    written = 0
    with path.open("wb") as fh:
        while written < size:
            chunk = pattern
            remaining = size - written
            if len(chunk) > remaining:
                chunk = pattern[:remaining]
            fh.write(chunk)
            written += len(chunk)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: generate_test_file.py PATH SIZE_BYTES SEED", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3])

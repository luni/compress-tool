#!/usr/bin/env python3
import pathlib
import sys
import zipfile


def main(archive: str, base_dir: str, compression: str, *paths: str) -> None:
    compression_map = {
        "store": getattr(zipfile, "ZIP_STORED"),
        "deflate": getattr(zipfile, "ZIP_DEFLATED"),
        "bzip2": getattr(zipfile, "ZIP_BZIP2", None),
        "lzma": getattr(zipfile, "ZIP_LZMA", None),
    }

    compression_type = compression_map.get(compression)
    if compression_type is None:
        print(f"Unsupported ZIP compression: {compression}", file=sys.stderr)
        sys.exit(3)

    base_path = pathlib.Path(base_dir)
    try:
        with zipfile.ZipFile(archive, "w", compression=compression_type, allowZip64=True) as zf:
            for rel in paths:
                zf.write(base_path / rel, arcname=rel)
    except RuntimeError as exc:
        print(f"Failed to write ZIP archive: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "Usage: create_zip_with_compression.py ARCHIVE BASE_DIR COMPRESSION PATH...",
            file=sys.stderr,
        )
        sys.exit(2)
    main(*sys.argv[1:])

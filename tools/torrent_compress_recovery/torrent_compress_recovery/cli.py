"""CLI entrypoint for torrent-compress-recovery."""

import argparse
import logging
from pathlib import Path

from .core import recover
from .gzip import format_gzip_header, parse_gzip_header
from .verify import verify_last_piece_against_raw


def main(argv: list[str] | None = None) -> int:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    ap = argparse.ArgumentParser(
        description=(
            "Recover compressed files referenced by a .torrent by searching for matching files in two input folders. "
            "Folder structure in inputs is ignored; files are matched by basename. "
            "If a compressed file is not found, the tool can optionally compress the corresponding raw file."
        )
    )
    ap.add_argument(
        "--header-info",
        action="store_true",
        help="Step A: Show gzip header info for partial files and exit",
    )
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help="Step B: Verify raw files against gzip trailers (last piece) and exit",
    )
    ap.add_argument(
        "--brute-force",
        action="store_true",
        help="Step C: Enable brute-force candidate generation (default: enabled in reproduce mode)",
    )
    ap.add_argument("torrent", type=Path)
    ap.add_argument("raw_dir", type=Path, help="Folder containing uncompressed raw data")
    ap.add_argument("partial_dir", type=Path, help="Folder containing partially/fully downloaded compressed files")
    ap.add_argument("target_dir", type=Path, help="Output folder")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--raw-fallback",
        action="store_true",
        help="If a required compressed file is not found in partial_dir, try compressing the corresponding raw file (basename without extension)",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )

    args = ap.parse_args(argv)

    if args.header_info:
        # Step A: display gzip header info for partial files
        for p in args.partial_dir.rglob("*"):
            if p.is_file():
                header = parse_gzip_header(p)
                if header is None:
                    continue
                logging.info(f"--- {p.relative_to(args.partial_dir)} ---")
                logging.info(format_gzip_header(header))
                logging.info("")
        return 0

    if args.verify_only:
        # Step B: verify raw files against gzip trailers (last piece)
        results = verify_last_piece_against_raw(args.torrent, args.raw_dir, args.partial_dir)
        any_missing = False
        for name, ok in results.items():
            status = "OK" if ok else "FAIL"
            logging.info(f"{name}: {status}")
            if not ok:
                any_missing = True
        return 1 if any_missing else 0

    result = recover(
        torrent_path=args.torrent,
        raw_dir=args.raw_dir,
        partial_dir=args.partial_dir,
        target_dir=args.target_dir,
        raw_fallback=args.raw_fallback,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    torrent_name = args.torrent.stem
    out_root = args.target_dir / torrent_name
    logging.info(f"torrent: {torrent_name}")
    logging.info(f"output:  {out_root}")
    logging.info(f"recovered_from_partial: {result.recovered}")
    logging.info(f"compressed_from_raw:    {result.gzipped}")
    logging.info(f"skipped_existing:       {result.skipped}")
    logging.info(f"missing:                {result.missing}")

    return 0 if result.missing == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

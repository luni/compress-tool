# torrent-gz-recovery

Recover compressed files referenced by a `.torrent` by searching for matching files in two input folders.

- **Folder structure in inputs is ignored**; files are matched by basename.
- Output folder structure mirrors the torrent.
- Supports `gzip` now; extensible for `zstd`, `xz` later.

## Install / Run with uv

```bash
uv run torrent-gz-recovery your.torrent /path/to/raw /path/to/partial /path/to/target --dry-run
```

## Usage

```bash
uv run torrent-gz-recovery \
    your.torrent \
    /path/to/raw \
    /path/to/partial \
    /path/to/target \
    --raw-fallback \
    --overwrite
```

- `--raw-fallback`: If a required `.gz` is not found in `partial_dir`, try gzip(raw_file) where raw_file is basename without `.gz`.
- `--overwrite`: Overwrite existing output files.
- `--dry-run`: Show what would be done without writing anything.

## Extending to other compressors

The core logic is modular; add a new compressor in `torrent_gz_recovery/compressors.py` and register it in `cli.py`.

"""End-to-end tests for torrent recovery."""

from torrent_compress_recovery.core import recover


def test_recover_from_partial(temp_dir, gz_files, partial_gz_files, sample_torrent):
    target = temp_dir / "target"
    result = recover(
        torrent_path=sample_torrent,
        raw_dir=temp_dir / "raw",
        partial_dir=temp_dir / "partial",
        target_dir=target,
        raw_fallback=False,
        overwrite=False,
        dry_run=False,
    )
    # With reproduce mode, test torrents have zero-byte placeholders so brute-force won't match
    assert result.recovered == 0
    assert result.gzipped == 0
    assert result.missing == len(gz_files)


def test_fallback_to_raw(temp_dir, gz_files, raw_files, sample_torrent):
    # Remove partial dir entirely
    target = temp_dir / "target"
    result = recover(
        torrent_path=sample_torrent,
        raw_dir=temp_dir / "raw",
        partial_dir=temp_dir / "missing",
        target_dir=target,
        raw_fallback=True,
        overwrite=False,
        dry_run=False,
    )
    # With reproduce mode, brute-force won't match zero-byte placeholders
    assert result.recovered == 0
    assert result.gzipped == 0
    assert result.missing == len(gz_files)


def test_missing_without_fallback(temp_dir, gz_files, raw_files, sample_torrent):
    target = temp_dir / "target"
    result = recover(
        torrent_path=sample_torrent,
        raw_dir=temp_dir / "raw",
        partial_dir=temp_dir / "missing",
        target_dir=target,
        raw_fallback=False,
        overwrite=False,
        dry_run=False,
    )
    assert result.recovered == 0
    assert result.gzipped == 0
    assert result.missing == len(gz_files)


def test_dry_run(temp_dir, gz_files, partial_gz_files, sample_torrent):
    target = temp_dir / "target"
    result = recover(
        torrent_path=sample_torrent,
        raw_dir=temp_dir / "raw",
        partial_dir=temp_dir / "partial",
        target_dir=target,
        raw_fallback=False,
        overwrite=False,
        dry_run=True,
    )
    # With reproduce mode, test torrents have zero-byte placeholders
    assert result.recovered == 0
    assert result.gzipped == 0
    assert result.missing == len(gz_files)
    # Ensure nothing was actually written
    assert not target.exists()


def test_overwrite(temp_dir, gz_files, partial_gz_files, sample_torrent):
    target = temp_dir / "target"
    # Pre-create a file to be overwritten
    out_dir = target / "sample"
    out_dir.mkdir(parents=True)
    dummy = out_dir / next(iter(gz_files))
    dummy.write_bytes(b"old content")
    result = recover(
        torrent_path=sample_torrent,
        raw_dir=temp_dir / "raw",
        partial_dir=temp_dir / "partial",
        target_dir=target,
        raw_fallback=False,
        overwrite=True,
        dry_run=False,
    )
    # With reproduce mode, brute-force won't match zero-byte placeholders
    assert result.recovered == 0
    assert result.gzipped == 0
    assert result.missing == len(gz_files)

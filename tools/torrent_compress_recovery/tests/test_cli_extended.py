"""Extended tests for CLI module to improve coverage."""

from torrent_compress_recovery.cli import main


def test_main_help():
    """Test CLI help functionality."""
    import sys
    from unittest.mock import patch

    # Test help flag
    with patch.object(sys, "argv", ["torrent_compress_recovery", "--help"]):
        try:
            main()
        except SystemExit as e:
            # Help should exit with code 0
            assert e.code == 0


def test_main_invalid_args():
    """Test CLI with invalid arguments."""
    import sys
    from unittest.mock import patch

    # Test invalid arguments
    with patch.object(sys, "argv", ["torrent_compress_recovery", "--invalid-flag"]):
        try:
            main()
        except SystemExit as e:
            # Invalid args should exit with code 2
            assert e.code == 2


def test_main_no_args():
    """Test CLI with no arguments."""
    import sys
    from unittest.mock import patch

    # Test no arguments (should show help)
    with patch.object(sys, "argv", ["torrent_compress_recovery"]):
        try:
            main()
        except SystemExit as e:
            # No args should exit with code 2 (missing required args)
            assert e.code == 2

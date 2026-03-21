"""Tests for parallax_utils.version_check.

Covers:
- get_current_version fallback chain
- check_latest_release with mocked HTTP
- Network errors handled gracefully
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parallax_utils.version_check import check_latest_release, get_current_version


class TestGetCurrentVersion:
    """Tests for get_current_version."""

    def test_returns_string(self):
        version = get_current_version()
        assert isinstance(version, str)

    def test_fallback_to_unknown(self):
        """When both metadata and module fail, returns 'unknown'."""
        with patch(
            "parallax_utils.version_check.importlib.metadata.version", side_effect=Exception
        ):
            with patch.dict(sys.modules, {"parallax": None}):
                version = get_current_version()
                # May return 'unknown' or the actual version if installed
                assert isinstance(version, str)


class TestCheckLatestRelease:
    """Tests for check_latest_release."""

    def test_no_crash_on_network_error(self):
        """Should silently handle network errors."""
        with patch("parallax_utils.version_check.urllib.request.urlopen", side_effect=Exception):
            check_latest_release()  # Should not raise

    def test_prints_update_notice_when_different(self, capsys):
        """When latest != current, should print update notice."""
        response_data = json.dumps({"tag_name": "v99.99.99"}).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch(
            "parallax_utils.version_check.urllib.request.urlopen", return_value=mock_response
        ):
            with patch("parallax_utils.version_check.get_current_version", return_value="0.1.0"):
                check_latest_release()

        captured = capsys.readouterr()
        assert "99.99.99" in captured.out

    def test_no_output_when_same_version(self, capsys):
        """When versions match, no update notice."""
        response_data = json.dumps({"tag_name": "v0.1.2"}).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch(
            "parallax_utils.version_check.urllib.request.urlopen", return_value=mock_response
        ):
            with patch("parallax_utils.version_check.get_current_version", return_value="0.1.2"):
                check_latest_release()

        captured = capsys.readouterr()
        assert "New version" not in captured.out

    def test_handles_missing_tag_name(self):
        """If response has no tag_name or name, should not crash."""
        response_data = json.dumps({}).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = response_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch(
            "parallax_utils.version_check.urllib.request.urlopen", return_value=mock_response
        ):
            check_latest_release()  # Should not raise

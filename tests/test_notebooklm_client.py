"""
Unit tests for pipeline/notebooklm_client.py
"""

import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.notebooklm_client import (
    NotebookLMClient,
    NotebookLMError,
    RateLimitError,
    AuthenticationError,
    QUOTA_FILE,
)


@pytest.fixture(autouse=True)
def isolated_quota_file(tmp_path, monkeypatch):
    """Redirect quota file to a temp dir for each test."""
    quota_path = tmp_path / "notebooklm_quota.json"
    monkeypatch.setattr("pipeline.notebooklm_client.QUOTA_FILE", quota_path)
    monkeypatch.setattr("pipeline.notebooklm_client.QUOTA_FILE_DIR", tmp_path)
    return quota_path


class TestQuotaTracking:
    """Tests for local quota tracking."""

    def test_initial_quota_is_full(self):
        client = NotebookLMClient(daily_quota=50)
        assert client.get_remaining_quota() == 50

    def test_increment_quota(self):
        client = NotebookLMClient(daily_quota=50)
        client.increment_quota()
        client.increment_quota()
        assert client.get_remaining_quota() == 48

    def test_quota_resets_next_day(self, isolated_quota_file):
        # Simulate yesterday's used quota
        yesterday = str(date.today() - timedelta(days=1))
        isolated_quota_file.write_text(
            json.dumps({"date": yesterday, "used": 50}),
            encoding="utf-8",
        )
        client = NotebookLMClient(daily_quota=50)
        assert client.get_remaining_quota() == 50

    def test_quota_info_structure(self):
        client = NotebookLMClient(daily_quota=30)
        info = client.get_quota_info()
        assert "date" in info
        assert "used" in info
        assert "remaining" in info
        assert "limit" in info
        assert info["limit"] == 30

    def test_quota_never_negative(self, isolated_quota_file):
        # Simulate over-used quota
        isolated_quota_file.write_text(
            json.dumps({"date": str(date.today()), "used": 999}),
            encoding="utf-8",
        )
        client = NotebookLMClient(daily_quota=50)
        assert client.get_remaining_quota() == 0


class TestAskQuestion:
    """Tests for ask_question method."""

    def _make_success_response(self, answer: str) -> dict:
        """Simulate a successful MCP tool response."""
        return {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "success",
                            "answer": answer,
                            "session_id": "abc123",
                            "notebook_url": "https://notebooklm.google.com/notebook/test",
                        }),
                    }
                ]
            },
        }

    def _make_error_response(self, message: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": 2,
            "error": {"code": -32000, "message": message},
        }

    @patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
    def test_successful_question(self, mock_call):
        mock_call.return_value = self._make_success_response("這是答案")
        client = NotebookLMClient(daily_quota=50)
        result = client.ask_question("什麼是禪定？")
        assert result["success"] is True
        assert result["answer"] == "這是答案"
        assert result["session_id"] == "abc123"

    @patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
    def test_ask_question_increments_quota(self, mock_call):
        mock_call.return_value = self._make_success_response("答案")
        client = NotebookLMClient(daily_quota=50)
        before = client.get_remaining_quota()
        client.ask_question("問題")
        assert client.get_remaining_quota() == before - 1

    def test_rate_limit_when_quota_exhausted(self, isolated_quota_file):
        isolated_quota_file.write_text(
            json.dumps({"date": str(date.today()), "used": 50}),
            encoding="utf-8",
        )
        client = NotebookLMClient(daily_quota=50)
        with pytest.raises(RateLimitError):
            client.ask_question("問題")

    @patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
    def test_rate_limit_error_from_mcp(self, mock_call):
        mock_call.return_value = self._make_error_response("rate limit exceeded")
        client = NotebookLMClient(daily_quota=50)
        with pytest.raises(RateLimitError):
            client.ask_question("問題")

    @patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
    def test_auth_error_from_mcp(self, mock_call):
        mock_call.return_value = self._make_error_response("authentication required")
        client = NotebookLMClient(daily_quota=50)
        with pytest.raises(AuthenticationError):
            client.ask_question("問題")

    @patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
    def test_generic_error_from_mcp(self, mock_call):
        mock_call.return_value = self._make_error_response("some unknown error")
        client = NotebookLMClient(daily_quota=50)
        with pytest.raises(NotebookLMError):
            client.ask_question("問題")

    @patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
    def test_question_with_notebook_url(self, mock_call):
        mock_call.return_value = self._make_success_response("答案")
        client = NotebookLMClient(daily_quota=50)
        result = client.ask_question(
            "問題",
            notebook_url="https://notebooklm.google.com/notebook/mytest",
        )
        assert result["success"] is True
        # Verify notebook_url was passed in params
        call_args = mock_call.call_args
        params = call_args[0][1]
        assert params["notebook_url"] == "https://notebooklm.google.com/notebook/mytest"

    @patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
    def test_question_with_session_id(self, mock_call):
        mock_call.return_value = self._make_success_response("答案")
        client = NotebookLMClient(daily_quota=50)
        client.ask_question("問題", session_id="existing-session")
        call_args = mock_call.call_args
        params = call_args[0][1]
        assert params["session_id"] == "existing-session"


class TestNpxNotFound:
    """Test behavior when npx is not available."""

    def test_raises_on_missing_npx(self):
        client = NotebookLMClient(npx_command="/nonexistent/npx")
        with pytest.raises(NotebookLMError, match="Cannot find"):
            client._call_mcp("get_health")

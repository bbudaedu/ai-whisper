"""
Unit tests for pipeline/notebooklm_scheduler.py
"""

import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.notebooklm_client import RateLimitError
from pipeline.notebooklm_scheduler import NotebookLMScheduler, TaskStatus, QueueItem
from pipeline.notebooklm_tasks import OutputType


def make_mock_client(
    daily_quota: int = 50,
    remaining: int = 50,
    ask_response: dict | None = None,
) -> MagicMock:
    """Create a mock NotebookLMClient."""
    client = MagicMock()
    client.daily_quota = daily_quota
    client.get_remaining_quota.return_value = remaining
    client.get_quota_info.return_value = {
        "date": str(date.today()),
        "used": daily_quota - remaining,
        "remaining": remaining,
        "limit": daily_quota,
    }
    if ask_response is None:
        ask_response = {
            "success": True,
            "answer": "# 心智圖\n\n```mermaid\nmindmap\n  root(測試)\n```",
            "session_id": "sess123",
            "notebook_url": "https://notebooklm.google.com/test",
        }
    client.ask_question.return_value = ask_response
    return client


def make_scheduler(tmp_path: Path, client: MagicMock | None = None) -> NotebookLMScheduler:
    """Create a scheduler with a temp queue file."""
    queue_file = str(tmp_path / "test_queue.json")
    if client is None:
        client = make_mock_client()
    return NotebookLMScheduler(
        queue_file=queue_file,
        notebook_url="https://notebooklm.google.com/test",
        client=client,
        daily_quota=50,
    )


class TestEnqueue:
    """Tests for queue management."""

    def test_enqueue_episode_adds_all_5_tasks(self, tmp_path):
        scheduler = make_scheduler(tmp_path)
        count = scheduler.enqueue_episode(
            episode_id="vid001",
            episode_dir=str(tmp_path),
            title="佛教公案選集017",
        )
        assert count == 5
        assert scheduler.get_pending_count() == 5

    def test_enqueue_does_not_duplicate_pending_tasks(self, tmp_path):
        scheduler = make_scheduler(tmp_path)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")
        count2 = scheduler.enqueue_episode("vid001", str(tmp_path), "標題")
        assert count2 == 0
        assert scheduler.get_pending_count() == 5

    def test_enqueue_skips_existing_files(self, tmp_path):
        from pipeline.notebooklm_tasks import get_output_path, save_output
        # Pre-create mindmap output
        mindmap_path = get_output_path(str(tmp_path), "標題", OutputType.MINDMAP)
        save_output(mindmap_path, "existing mindmap")

        scheduler = make_scheduler(tmp_path)
        count = scheduler.enqueue_episode("vid001", str(tmp_path), "標題", skip_existing=True)
        assert count == 4  # 5 - 1 existing

    def test_enqueue_specific_output_types(self, tmp_path):
        scheduler = make_scheduler(tmp_path)
        count = scheduler.enqueue_episode(
            "vid001", str(tmp_path), "標題",
            output_types=[OutputType.MINDMAP, OutputType.SUMMARY],
        )
        assert count == 2

    def test_queue_persists_to_file(self, tmp_path):
        queue_file = str(tmp_path / "q.json")
        s1 = NotebookLMScheduler(
            queue_file=queue_file,
            notebook_url="https://n.g.com",
            client=make_mock_client(),
        )
        s1.enqueue_episode("vid001", str(tmp_path), "標題")

        # Load a new scheduler from same file
        s2 = NotebookLMScheduler(
            queue_file=queue_file,
            notebook_url="https://n.g.com",
            client=make_mock_client(),
        )
        assert s2.get_pending_count() == 5


class TestGetQueueSummary:
    """Tests for queue summary."""

    def test_summary_counts_by_status(self, tmp_path):
        scheduler = make_scheduler(tmp_path)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")
        summary = scheduler.get_queue_summary()
        assert summary["total"] == 5
        assert summary["by_status"].get("pending", 0) == 5

    def test_summary_includes_quota(self, tmp_path):
        client = make_mock_client(remaining=45)
        scheduler = make_scheduler(tmp_path, client)
        summary = scheduler.get_queue_summary()
        assert summary["quota"]["remaining"] == 45


class TestProcessNext:
    """Tests for sequential task execution."""

    def test_processes_first_pending_task(self, tmp_path):
        client = make_mock_client()
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")
        result = scheduler.process_next("校對文本內容")
        assert result is not None
        assert result.success is True
        assert scheduler.get_pending_count() == 4

    def test_returns_none_when_queue_empty(self, tmp_path):
        scheduler = make_scheduler(tmp_path)
        result = scheduler.process_next("文本")
        assert result is None

    def test_pauses_when_quota_exhausted(self, tmp_path):
        client = make_mock_client(remaining=0)
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")
        result = scheduler.process_next("文本")
        assert result is not None
        assert result.success is False
        assert "quota" in result.error.lower()
        # Task should remain pending (not failed)
        assert scheduler.get_pending_count() == 5

    def test_marks_task_failed_on_error(self, tmp_path):
        client = make_mock_client()
        client.ask_question.side_effect = Exception("Connection error")
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題",
                                   output_types=[OutputType.MINDMAP])
        result = scheduler.process_next("文本")
        assert result.success is False
        # Item should now be marked failed
        items = scheduler.get_queue_items(status_filter="failed")
        assert len(items) == 1

    def test_re_queues_on_rate_limit_error(self, tmp_path):
        client = make_mock_client()
        client.ask_question.side_effect = RateLimitError("rate limit")
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題",
                                   output_types=[OutputType.MINDMAP])
        result = scheduler.process_next("文本")
        assert result.success is False
        # Should remain pending, not failed
        assert scheduler.get_pending_count() == 1

    def test_output_file_created_on_success(self, tmp_path):
        client = make_mock_client()
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題",
                                   output_types=[OutputType.MINDMAP])
        result = scheduler.process_next("文本")
        assert result.success is True
        assert os.path.exists(result.filepath)


class TestRunAll:
    """Tests for batch execution."""

    def test_run_all_processes_all_tasks(self, tmp_path):
        client = make_mock_client()
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")

        results = scheduler.run_all(
            get_text_func=lambda eid, edir: "文本",
            delay_between_tasks=0,
        )
        assert len(results) == 5
        assert all(r.success for r in results)

    def test_run_all_stops_on_quota_exhaustion(self, tmp_path):
        # First call succeeds, then quota runs out
        client = make_mock_client(remaining=2)
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")

        results = scheduler.run_all(
            get_text_func=lambda eid, edir: "文本",
            delay_between_tasks=0,
            max_tasks=2,
        )
        assert len(results) == 2

    def test_run_all_respects_max_tasks(self, tmp_path):
        client = make_mock_client()
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")

        results = scheduler.run_all(
            get_text_func=lambda eid, edir: "文本",
            delay_between_tasks=0,
            max_tasks=3,
        )
        assert len(results) == 3


class TestClearCompleted:
    """Tests for queue maintenance."""

    def test_clear_completed_removes_done_items(self, tmp_path):
        client = make_mock_client()
        scheduler = make_scheduler(tmp_path, client)
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題",
                                   output_types=[OutputType.MINDMAP])
        scheduler.process_next("文本")  # Completes the task

        removed = scheduler.clear_completed()
        assert removed == 1
        assert scheduler.get_pending_count() == 0

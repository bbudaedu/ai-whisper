"""
E2E-style integration test for the NotebookLM post-processing pipeline.
Mocks all NotebookLM network calls; tests file-system and queue flow end-to-end.
"""

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.notebooklm_client import NotebookLMClient
from pipeline.notebooklm_scheduler import NotebookLMScheduler, TaskStatus
from pipeline.notebooklm_tasks import OutputType, get_output_path


def make_mock_client(daily_quota: int = 50) -> MagicMock:
    client = MagicMock(spec=NotebookLMClient)
    client.daily_quota = daily_quota
    client.get_remaining_quota.return_value = daily_quota
    client.get_quota_info.return_value = {
        "date": str(date.today()),
        "used": 0,
        "remaining": daily_quota,
        "limit": daily_quota,
    }
    client.ask_question.return_value = {
        "success": True,
        "answer": "# 測試產出\n\n```mermaid\nmindmap\n  root(佛法)\n```",
        "session_id": "test-session",
        "notebook_url": "https://notebooklm.google.com/notebook/test",
    }
    # Simulate quota decrement on each call
    call_count = {"n": 0}
    def decrement_remaining(*args, **kwargs):
        call_count["n"] += 1
        client.get_remaining_quota.return_value = daily_quota - call_count["n"]
        return {
            "success": True,
            "answer": f"# 測試產出 {call_count['n']}\n\n內容",
            "session_id": "test-session",
        }
    client.ask_question.side_effect = decrement_remaining

    return client


class TestFullPipelineFlow:
    """Simulate the end-to-end flow: enqueue → execute → verify files."""

    def test_full_flow_all_5_outputs(self, tmp_path):
        """Complete pipeline: one episode → 5 output files created."""
        client = make_mock_client(daily_quota=50)
        queue_file = str(tmp_path / "queue.json")

        scheduler = NotebookLMScheduler(
            queue_file=queue_file,
            notebook_url="https://notebooklm.google.com/test",
            client=client,
            daily_quota=50,
        )

        # 1. Enqueue episode
        enqueued = scheduler.enqueue_episode(
            episode_id="T097V017_test",
            episode_dir=str(tmp_path),
            title="佛教公案選集017_E2E測試",
        )
        assert enqueued == 5

        # 2. Run all tasks
        results = scheduler.run_all(
            get_text_func=lambda eid, edir: "南無本師釋迦摩尼佛\n\n這是測試文本，包含佛法精義。",
            delay_between_tasks=0,
        )

        # 3. Verify results
        assert len(results) == 5
        assert all(r.success for r in results)

        # 4. Verify output files on disk
        nlm_dir = tmp_path / "notebooklm"
        assert nlm_dir.is_dir()
        md_files = list(nlm_dir.glob("*.md"))
        assert len(md_files) == 5

        # 5. Verify queue is now empty of pending tasks
        assert scheduler.get_pending_count() == 0

    def test_skip_existing_on_rerun(self, tmp_path):
        """Re-running should skip already-completed outputs."""
        client = make_mock_client(daily_quota=50)
        queue_file = str(tmp_path / "queue.json")

        scheduler = NotebookLMScheduler(
            queue_file=queue_file,
            notebook_url="https://notebooklm.google.com/test",
            client=client,
        )

        # First run: complete all 5
        scheduler.enqueue_episode("vid001", str(tmp_path), "測試標題")
        scheduler.run_all(
            get_text_func=lambda eid, edir: "文本",
            delay_between_tasks=0,
        )
        scheduler.clear_completed()

        # Second run: all skipped
        enqueued2 = scheduler.enqueue_episode(
            "vid001", str(tmp_path), "測試標題", skip_existing=True
        )
        assert enqueued2 == 0

    def test_quota_exhaustion_mid_run(self, tmp_path):
        """When quota runs out mid-run, remaining tasks stay pending."""
        client = MagicMock(spec=NotebookLMClient)
        client.daily_quota = 50

        # Allow first 3 calls, then return 0 remaining
        call_count = {"n": 0}
        def quota_countdown(*args, **kwargs):
            call_count["n"] += 1
            return max(0, 3 - call_count["n"])
        client.get_remaining_quota.side_effect = quota_countdown
        client.get_quota_info.return_value = {"date": str(date.today()), "used": 47, "remaining": 3, "limit": 50}
        client.ask_question.return_value = {
            "success": True,
            "answer": "答案",
            "session_id": "s",
        }

        scheduler = NotebookLMScheduler(
            queue_file=str(tmp_path / "q.json"),
            notebook_url="https://notebooklm.google.com/test",
            client=client,
        )
        scheduler.enqueue_episode("vid001", str(tmp_path), "標題")
        results = scheduler.run_all(
            get_text_func=lambda eid, edir: "文本",
            delay_between_tasks=0,
        )

        # Should have stopped before all 5 are done
        assert len(results) < 5
        assert scheduler.get_pending_count() > 0

    def test_queue_survives_restart(self, tmp_path):
        """Queue persists across scheduler restarts (simulates next day resume)."""
        queue_file = str(tmp_path / "queue.json")
        client = make_mock_client()

        s1 = NotebookLMScheduler(
            queue_file=queue_file,
            notebook_url="https://notebooklm.google.com/test",
            client=client,
        )
        s1.enqueue_episode("vid001", str(tmp_path), "標題",
                            output_types=[OutputType.MINDMAP, OutputType.SUMMARY])

        # Simulate restart
        s2 = NotebookLMScheduler(
            queue_file=queue_file,
            notebook_url="https://notebooklm.google.com/test",
            client=client,
        )
        assert s2.get_pending_count() == 2
        results = s2.run_all(
            get_text_func=lambda eid, edir: "文本",
            delay_between_tasks=0,
        )
        assert len(results) == 2
        assert all(r.success for r in results)


class TestAutoNotebooklmScript:
    """Tests for the auto_notebooklm.py orchestrator logic."""

    def test_read_text_from_srt(self, tmp_path):
        from auto_notebooklm import _extract_text_from_srt
        srt_content = (
            "1\n00:00:01,000 --> 00:00:05,000\n南無本師釋迦摩尼佛\n\n"
            "2\n00:00:05,000 --> 00:00:10,000\n這是第二段\n\n"
        )
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content, encoding="utf-8")
        text = _extract_text_from_srt(str(srt_file))
        assert "南無本師釋迦摩尼佛" in text
        assert "00:00:01,000" not in text  # timestamps stripped
        assert "\n1\n" not in text  # indices stripped

    def test_read_text_prefers_proofread_srt(self, tmp_path):
        from auto_notebooklm import read_text_content
        regular_srt = tmp_path / "ep.srt"
        proofread_srt = tmp_path / "ep_proofread.srt"
        regular_srt.write_text("1\n00:00:01,000 --> 00:00:05,000\n普通版\n\n", encoding="utf-8")
        proofread_srt.write_text("1\n00:00:01,000 --> 00:00:05,000\n校對版\n\n", encoding="utf-8")

        text = read_text_content("vid", str(tmp_path))
        assert "校對版" in text

    def test_read_text_fallback_to_txt(self, tmp_path):
        from auto_notebooklm import read_text_content
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("TXT 備用內容", encoding="utf-8")

        text = read_text_content("vid", str(tmp_path))
        assert "TXT 備用內容" in text

    def test_read_text_empty_when_no_files(self, tmp_path):
        from auto_notebooklm import read_text_content
        text = read_text_content("vid", str(tmp_path))
        assert text == ""

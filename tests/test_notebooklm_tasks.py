"""
Unit tests for pipeline/notebooklm_tasks.py
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.notebooklm_tasks import (
    OutputType,
    TaskResult,
    build_prompt,
    check_existing_outputs,
    get_output_path,
    parse_response,
    save_output,
)


class TestBuildPrompt:
    """Tests for prompt template generation."""

    def test_mindmap_contains_mermaid_instruction(self):
        prompt = build_prompt(OutputType.MINDMAP, "測試標題", "內容")
        assert "mindmap" in prompt.lower() or "Mermaid" in prompt

    def test_presentation_contains_slide_separator(self):
        prompt = build_prompt(OutputType.PRESENTATION, "測試標題", "內容")
        assert "---" in prompt

    def test_summary_requests_structured_output(self):
        prompt = build_prompt(OutputType.SUMMARY, "測試標題", "內容")
        assert "摘要" in prompt or "summary" in prompt.lower()

    def test_infographic_full_requests_detailed(self):
        prompt = build_prompt(OutputType.INFOGRAPHIC_FULL, "測試標題", "內容")
        assert "完整" in prompt or "詳盡" in prompt or "標準" in prompt

    def test_infographic_compact_requests_brief(self):
        prompt = build_prompt(OutputType.INFOGRAPHIC_COMPACT, "測試標題", "內容")
        assert "精簡" in prompt

    def test_title_is_embedded_in_prompt(self):
        title = "佛教公案選集017_簡豐文居士"
        prompt = build_prompt(OutputType.MINDMAP, title, "內容")
        assert title in prompt

    def test_text_truncation_at_4000_chars(self):
        long_text = "a" * 5000
        prompt = build_prompt(OutputType.SUMMARY, "標題", long_text)
        # Prompt should reference truncation
        assert "truncated" in prompt or len(prompt) < 5500

    def test_all_output_types_return_non_empty_prompt(self):
        for ot in OutputType:
            prompt = build_prompt(ot, "標題", "內容")
            assert len(prompt) > 50


class TestParseResponse:
    """Tests for response parsing and cleanup."""

    def test_mindmap_extracts_mermaid_block(self):
        raw = "這是說明\n\n```mermaid\nmindmap\n  root(佛教)\n```\n\n其他說明"
        result = parse_response(OutputType.MINDMAP, raw)
        assert "```mermaid" in result
        assert "mindmap" in result

    def test_strips_followup_reminder(self):
        raw = "答案內容\n\nEXTREMELY IMPORTANT: Is that ALL you need to know? 請繼續問"
        result = parse_response(OutputType.SUMMARY, raw)
        assert "EXTREMELY IMPORTANT" not in result

    def test_empty_response_returns_empty(self):
        assert parse_response(OutputType.SUMMARY, "") == ""

    def test_presentation_keeps_markdown_structure(self):
        raw = "# 標題\n---\n## 投影片一\n- 重點1\n---\n## 投影片二"
        result = parse_response(OutputType.PRESENTATION, raw)
        assert "---" in result

    def test_mindmap_without_mermaid_returns_raw_cleaned(self):
        raw = "心智圖：中心 → 概念一 → 細節"
        result = parse_response(OutputType.MINDMAP, raw)
        assert "心智圖" in result


class TestGetOutputPath:
    """Tests for output path computation."""

    def test_output_path_in_notebooklm_subdir(self):
        path = get_output_path("/tmp/T097V017", "佛教公案選集017", OutputType.MINDMAP)
        assert "/notebooklm/" in path
        assert path.endswith("_mindmap.md")

    def test_output_path_sanitizes_special_chars(self):
        path = get_output_path("/tmp/ep", "標題:含/特殊?字元", OutputType.SUMMARY)
        # Special characters should be replaced
        assert ":" not in os.path.basename(path)
        assert "/" not in os.path.basename(path)
        assert "?" not in os.path.basename(path)

    def test_all_output_types_have_correct_suffix(self):
        suffixes = {
            OutputType.MINDMAP: "_mindmap.md",
            OutputType.PRESENTATION: "_presentation.md",
            OutputType.SUMMARY: "_summary.md",
            OutputType.INFOGRAPHIC_FULL: "_infographic_full.md",
            OutputType.INFOGRAPHIC_COMPACT: "_infographic_compact.md",
        }
        for ot, expected_suffix in suffixes.items():
            path = get_output_path("/tmp/ep", "標題", ot)
            assert path.endswith(expected_suffix), f"{ot.value} should end with {expected_suffix}"


class TestSaveOutput:
    """Tests for file writing."""

    def test_saves_content_correctly(self, tmp_path):
        filepath = str(tmp_path / "notebooklm" / "test_mindmap.md")
        save_output(filepath, "# 心智圖")
        assert os.path.exists(filepath)
        assert "心智圖" in open(filepath, encoding="utf-8").read()

    def test_creates_parent_directories(self, tmp_path):
        nested_path = str(tmp_path / "a" / "b" / "c" / "out.md")
        save_output(nested_path, "content")
        assert os.path.exists(nested_path)


class TestCheckExistingOutputs:
    """Tests for existing output detection."""

    def test_detects_existing_files(self, tmp_path):
        title = "測試標題"
        ep_dir = str(tmp_path)
        # Create one output file
        nlm_dir = tmp_path / "notebooklm"
        nlm_dir.mkdir()
        path = get_output_path(ep_dir, title, OutputType.MINDMAP)
        save_output(path, "content")

        result = check_existing_outputs(ep_dir, title)
        assert result[OutputType.MINDMAP] is True
        assert result[OutputType.SUMMARY] is False

    def test_all_false_when_no_outputs(self, tmp_path):
        result = check_existing_outputs(str(tmp_path), "標題")
        assert all(v is False for v in result.values())


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_success_result(self):
        r = TaskResult(output_type=OutputType.MINDMAP, success=True, filepath="/tmp/out.md")
        assert r.success is True
        assert r.error == ""

    def test_failure_result(self):
        r = TaskResult(output_type=OutputType.SUMMARY, success=False, error="rate limit")
        assert r.success is False
        assert r.error == "rate limit"

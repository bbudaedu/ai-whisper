"""校對引擎測試套件
======================
"""

import pytest
import os
import json
import tempfile

from pipeline.proofreading_engine import ProofreadingEngine


@pytest.fixture
def skill_dir(tmp_path):
    """建立暫時 skill 資料夾。"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    dicts_dir = tmp_path / "dictionaries"
    dicts_dir.mkdir()

    # 寫入 proofread prompt
    (prompts_dir / "proofread.md").write_text(
        "校對以下字幕:\n{{lecture_section}}\n<字幕>\n{{srt_text}}\n</字幕>",
        encoding="utf-8"
    )
    (prompts_dir / "punctuate.md").write_text(
        "加標點:\n{{text}}",
        encoding="utf-8"
    )

    # 寫入字典
    errors = {
        "errors": [
            {"wrong": "釋迦摩尼佛", "correct": "釋迦牟尼佛"},
            {"wrong": "菩提薩埵", "correct": "菩提薩埱"},
        ]
    }
    (dicts_dir / "common_errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return str(tmp_path)


@pytest.fixture
def engine(skill_dir):
    return ProofreadingEngine(skill_dir=skill_dir)


class TestDictionaryLoading:
    def test_loads_errors_from_json(self, engine):
        assert len(engine.errors) == 2
        assert engine.errors[0]["wrong"] == "釋迦摩尼佛"

    def test_empty_dict_on_missing_file(self, tmp_path):
        engine = ProofreadingEngine(skill_dir=str(tmp_path))
        assert engine.errors == []


class TestPreCorrection:
    def test_replaces_known_errors(self, engine):
        text = "南無本師釋迦摩尼佛"
        result = engine.pre_correct(text)
        assert result == "南無本師釋迦牟尼佛"

    def test_replaces_multiple_errors(self, engine):
        text = "釋迦摩尼佛 菩提薩埵"
        result = engine.pre_correct(text)
        assert "釋迦牟尼佛" in result
        assert "菩提薩埱" in result

    def test_no_change_on_correct_text(self, engine):
        text = "釋迦牟尼佛"
        result = engine.pre_correct(text)
        assert result == text


class TestPromptBuilding:
    def test_build_prompt_basic(self, engine):
        prompt = engine.build_prompt("[1] 佛教公案")
        assert "[1] 佛教公案" in prompt
        assert "字幕" in prompt

    def test_build_prompt_with_lecture(self, engine):
        prompt = engine.build_prompt("[1] 佛教公案", "簡豐文居士主講")
        assert "講義" in prompt
        assert "簡豐文" in prompt

    def test_build_prompt_without_lecture(self, engine):
        prompt = engine.build_prompt("[1] 佛教公案", "")
        assert "講義" not in prompt

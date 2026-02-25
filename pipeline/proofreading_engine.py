"""校對引擎 — 載入 Skill 資料並套用
=====================================
從 skills/buddhist-proofreading/ 載入常錯字典和 prompt 模板，
提供預校正和 prompt 建立功能。
"""

import json
import os
import re
import logging

logger = logging.getLogger(__name__)

SKILL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "buddhist-proofreading"
)


class ProofreadingEngine:
    """佛教校對引擎：載入字典 + prompt 模板。"""

    def __init__(self, skill_dir=None):
        self.skill_dir = skill_dir or SKILL_DIR
        self._errors = None
        self._proofread_template = None
        self._punctuate_template = None

    @property
    def errors(self):
        if self._errors is None:
            self._errors = self._load_dictionary()
        return self._errors

    @property
    def proofread_template(self):
        if self._proofread_template is None:
            self._proofread_template = self._load_prompt("proofread.md")
        return self._proofread_template

    @property
    def punctuate_template(self):
        if self._punctuate_template is None:
            self._punctuate_template = self._load_prompt("punctuate.md")
        return self._punctuate_template

    def _load_dictionary(self):
        path = os.path.join(self.skill_dir, "dictionaries", "common_errors.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("errors", [])
        except FileNotFoundError:
            logger.warning(f"字典檔不存在: {path}")
            return []
        except Exception as e:
            logger.error(f"載入字典失敗: {e}")
            return []

    def _load_prompt(self, filename):
        path = os.path.join(self.skill_dir, "prompts", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt 檔不存在: {path}")
            return ""

    def pre_correct(self, text):
        """用常錯字典做第一輪正則替換。"""
        for entry in self.errors:
            wrong = entry.get("wrong", "")
            correct = entry.get("correct", "")
            if wrong and correct and wrong != correct:
                text = text.replace(wrong, correct)
        return text

    def build_prompt(self, srt_text, lecture_text=""):
        """從模板建立 prompt，注入字幕和講義內容。"""
        template = self.proofread_template
        if not template:
            return None

        lecture_section = ""
        if lecture_text:
            lecture_section = f"""
以下是上課講義內容（供你參考佛學詞彙正確用字）：
<講義>
{lecture_text[:3000]}
</講義>
"""
        prompt = template.replace("{{lecture_section}}", lecture_section)
        prompt = prompt.replace("{{srt_text}}", srt_text)
        return prompt

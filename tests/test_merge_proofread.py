"""合併校對+標點 測試套件
=========================
"""

import pytest
from pipeline.proofread_format import build_merged_prompt, parse_merged_response


class TestPromptGeneration:
    def test_basic_prompt_format(self):
        srt = "[1] 請最大的功念\n[2] 南無本師釋迦摩尼佛"
        prompt = build_merged_prompt(srt)
        assert "<校對版>" in prompt
        assert "<排版版>" in prompt
        assert "字幕" in prompt
        assert "[1] 請最大的功念" in prompt

    def test_prompt_with_lecture(self):
        srt = "[1] 佛教公案"
        lecture = "佛教公案選集 簡豐文居士主講"
        prompt = build_merged_prompt(srt, lecture)
        assert "講義" in prompt
        assert "簡豐文" in prompt

    def test_prompt_without_lecture(self):
        srt = "[1] 佛教公案"
        prompt = build_merged_prompt(srt, "")
        assert "講義" not in prompt


class TestResponseParsing:
    def test_valid_response(self):
        response = """<校對版>
[1] 佛教公案選集
[2] 簡豐文居士
</校對版>

<排版版>
佛教公案選集，簡豐文居士主講。
</排版版>"""
        proofread, formatted = parse_merged_response(response)
        assert "[1] 佛教公案選集" in proofread
        assert "佛教公案選集，" in formatted

    def test_empty_response(self):
        proofread, formatted = parse_merged_response("")
        assert proofread is None
        assert formatted is None

    def test_none_response(self):
        proofread, formatted = parse_merged_response(None)
        assert proofread is None
        assert formatted is None

    def test_malformed_response_partial(self):
        response = """<校對版>
[1] 佛教公案
</校對版>
No 排版版 section here"""
        proofread, formatted = parse_merged_response(response)
        assert proofread is not None
        assert formatted is None

    def test_whitespace_handling(self):
        response = """<校對版>
  [1] 佛教公案  
</校對版>

<排版版>
  佛教公案。  
</排版版>"""
        proofread, formatted = parse_merged_response(response)
        assert proofread == "[1] 佛教公案"
        assert formatted == "佛教公案。"

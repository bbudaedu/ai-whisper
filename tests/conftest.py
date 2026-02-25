"""共用 fixtures for ai-whisper tests."""

import pytest


@pytest.fixture
def mock_api_success_response():
    """模擬成功的 API 回應。"""
    return {
        "choices": [
            {
                "message": {
                    "content": "[1] 佛教公案選集\n[2] 簡豐文居士",
                    "reasoning_content": "",
                }
            }
        ]
    }


@pytest.fixture
def mock_api_reasoning_response():
    """模擬只有 reasoning_content 的回應（某些中轉模型）。"""
    return {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning_content": "[1] 佛教公案選集\n[2] 簡豐文居士",
                }
            }
        ]
    }


@pytest.fixture
def sample_srt_content():
    """SRT 字幕範本。"""
    return (
        "1\n"
        "00:00:01,000 --> 00:00:05,000\n"
        "請最大的功念三稱本師聖號\n\n"
        "2\n"
        "00:00:05,000 --> 00:00:10,000\n"
        "南無本師釋迦摩尼佛\n\n"
        "3\n"
        "00:00:10,000 --> 00:00:15,000\n"
        "無上聖身唯妙法\n"
    )


@pytest.fixture
def sample_subtitles():
    """解析後的字幕列表。"""
    return [
        {"idx": "1", "timestamp": "00:00:01,000 --> 00:00:05,000", "text": "請最大的功念三稱本師聖號"},
        {"idx": "2", "timestamp": "00:00:05,000 --> 00:00:10,000", "text": "南無本師釋迦摩尼佛"},
        {"idx": "3", "timestamp": "00:00:10,000 --> 00:00:15,000", "text": "無上聖身唯妙法"},
    ]

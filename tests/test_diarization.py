import pytest
from pipeline.diarization import run_diarization
import os

# 建立一個測試用的 dummy audio (不需要真的音檔，只要路徑存在即可，或者用一個靜音檔案)
@pytest.fixture
def dummy_audio_path(tmp_path):
    # 建立一個空檔案作為測試用，但 diarization 可能會讀取內容，這邊暫時假設它能處理
    # 真實測試應該提供一個短的 wav 檔
    audio_file = tmp_path / "test.wav"
    audio_file.write_text("dummy content")
    return str(audio_file)

def test_pipeline_loads_model():
    # 簡單驗證 pipeline 物件是否成功載入
    from pipeline.diarization import pipeline
    assert pipeline is not None

def test_run_diarization_invalid_file():
    with pytest.raises(FileNotFoundError):
        run_diarization("non_existent.wav")

# 備註: 由於 pyannote.audio 模型較大，完整測試需要 GPU 資源與模型權限
# 這邊採用 TDD RED 流程，若無法執行則說明原因

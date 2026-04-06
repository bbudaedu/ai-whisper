import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch

# 加入路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import auto_youtube_whisper

class TestE2EPipeline(unittest.TestCase):

    def setUp(self):
        # 建立臨時目錄模擬 NAS
        self.test_dir = tempfile.mkdtemp()
        self.fixture_audio = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures/test_audio.wav"))
        
    def tearDown(self):
        # 清理臨時目錄
        shutil.rmtree(self.test_dir)

    @patch("auto_youtube_whisper.download_audio")
    @patch("auto_youtube_whisper.send_email")
    @patch("auto_youtube_whisper.PROOFREAD_AVAILABLE", False) # 測試環境先不跑 Gemini 以免浪費 Quota
    def test_full_pipeline_flow(self, mock_email, mock_download):
        # 模擬影片資訊
        video = {"id": "e2e_test_vid", "title": "E2E Test Video 001"}
        
        # 模擬下載成功，直接指向 fixture audio
        mock_download.return_value = self.fixture_audio
        
        # 設定測試用的播放清單配置
        pl_config = {
            "id": "test_pl",
            "folder_prefix": "TEST",
            "whisper_model": "tiny", # 使用最小模型加快測試
            "whisper_lang": "en",
            "output_dir": self.test_dir
        }
        
        # 將 NAS_OUTPUT_BASE 暫時導向測試目錄
        with patch("auto_youtube_whisper.NAS_OUTPUT_BASE", self.test_dir):
            # 執行處理流程
            result = auto_youtube_whisper.process_video(video, pl_config)
            
            # 驗證結果
            self.assertTrue(result["success"])
            self.assertIn("episode_dir", result)
            
            episode_dir = result["episode_dir"]
            
            # 驗證檔案是否真的產生了
            # 由於 safe_title 是 "E2E_Test_Video_001", video_id 是 "e2e_test_vid"
            # 期望檔名舉例: E2E_Test_Video_001__e2e_test_vid.srt
            
            # 檢查是否存在基本的 SRT, TXT
            self.assertTrue(any(f.endswith(".srt") for f in os.listdir(episode_dir)))
            self.assertTrue(any(f.endswith(".txt") for f in os.listdir(episode_dir)))
            
            # 檢查報表是否產出 (Excel, Docx)
            # 注意: 如果環境中缺少 auto_postprocess 依賴，這塊會被 skip 並 log warning
            # 我們可以在這裡檢查是否有警告，或者假設環境完整
            
            # 驗證 Email 被呼叫（因為 actually_did_work 應該為 True）
            mock_email.assert_called_once()

if __name__ == "__main__":
    unittest.main()

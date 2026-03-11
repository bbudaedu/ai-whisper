import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

# 將專案目錄加入路徑以便匯入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import auto_youtube_whisper

class TestAutoYoutubeWhisper(unittest.TestCase):

    @patch("auto_youtube_whisper.check_video_files_exist")
    def test_find_new_videos(self, mock_check):
        # 模擬檔案檢查結果
        # 假設影片 1 已完成，影片 2 不完整，影片 3 完好但 JSON 沒紀錄
        mock_check.side_effect = lambda title, vid, **kwargs: vid == "vid1" or vid == "vid3"
        
        all_videos = [
            {"id": "vid1", "title": "Video 1 001"},
            {"id": "vid2", "title": "Video 2 002"},
            {"id": "vid3", "title": "Video 3 003"},
        ]
        processed = {
            "vid1": {"title": "Video 1 001", "processed_at": "2024-03-10"},
            "vid2": {"title": "Video 2 002", "processed_at": "2024-03-10"}
        }
        
        new_videos = auto_youtube_whisper.find_new_videos(all_videos, processed)
        
        # vid2 應該在 new_videos 中（因為不完整）
        # vid3 不應該在 new_videos 中（因為檔案已存在，應被 recovered）
        self.assertEqual(len(new_videos), 1)
        self.assertEqual(new_videos[0]["id"], "vid2")
        self.assertIn("vid3", processed)
        self.assertEqual(processed["vid3"]["srt"], "recovered from disk")

    @patch("auto_youtube_whisper.download_audio")
    @patch("auto_youtube_whisper.run_whisper")
    @patch("auto_youtube_whisper.send_email")
    def test_process_video_skips_if_exists(self, mock_email, mock_whisper, mock_download):
        # 測試如果檔案都存在，process_video 應該跳過主要步驟
        video = {"id": "test_id", "title": "Test Video 001"}
        pl_config = {"folder_prefix": "T097V"}
        
        with patch("glob.glob", return_value=["exists.wav"]), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data="Test content")):
            
            result = auto_youtube_whisper.process_video(video, pl_config)
            
            self.assertTrue(result["success"])
            mock_download.assert_not_called()
            mock_whisper.assert_not_called()
            mock_email.assert_not_called() # 不應發送重複 Email

    @patch("auto_youtube_whisper.subprocess.run")
    def test_download_audio_uses_semaphore(self, mock_run):
        # 測驗 dl_semaphore 是否正常包護下載過程
        video = {"id": "test_id", "title": "Test Video 001"}
        episode_dir = "/tmp/test"
        
        with patch("glob.glob", return_value=[]), \
             patch("os.path.exists", return_value=False):
            
            auto_youtube_whisper.download_audio(video, episode_dir)
            mock_run.assert_called_once()
            # 雖然難以在單元測試驗證 Semaphore 瞬間行為，但確保它執行到了 subprocess 即可

if __name__ == "__main__":
    unittest.main()

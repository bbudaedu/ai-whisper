import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 確保能載入 auto_postprocess (需設定 sys.path)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import auto_postprocess
from pipeline.api_client import ResilientAPIClient

class TestAutoPostprocessPunctuation(unittest.TestCase):

    @patch('auto_postprocess.config_data', {"punctuation_model": "gemini-2.5-flash"})
    def test_punctuation_model_config(self):
        """測試是否能正確讀取 punctuation_model 獨立設定"""
        import importlib
        importlib.reload(auto_postprocess)
        self.assertEqual(auto_postprocess.PUNCTUATION_MODEL, "gemini-2.5-flash")

    @patch('auto_postprocess.config_data', {"proofread_model": "gemini-3-flash"})
    def test_punctuation_model_fallback(self):
        """測試若無 punctuation_model，應預設為 gemini-2.5-flash (因在 get 指定了 default)"""
        import importlib
        importlib.reload(auto_postprocess)
        self.assertEqual(auto_postprocess.PUNCTUATION_MODEL, "gemini-2.5-flash")

    @patch('auto_postprocess._api_client')
    def test_call_gemini_api_uses_correct_client(self, mock_api_client):
        """單元測試：測試 call_gemini_api 確實呼叫了 _api_client.call"""
        mock_api_client.call.return_value = "測試標點。"
        result = auto_postprocess.call_gemini_api("請加上標點")
        
        mock_api_client.call.assert_called_once_with("請加上標點")
        self.assertEqual(result, "測試標點。")

    @patch('auto_postprocess.call_gemini_api')
    @patch('auto_postprocess.PUNCTUATION_CHUNK_SIZE', 2)
    def test_format_text_with_ai(self, mock_call_api):
        """單元測試：測試 format_text_with_ai 的分批邏輯與合併"""
        # 假設有 3 句，依 chunk size = 2 應該被分成兩批 (第一批2句，第二批1句)
        sentences = ["我是一句話", "這是第二句", "最後一句了"]
        
        # 設定 mock 回傳值，第一次呼叫回傳 A，第二次回傳 B
        mock_call_api.side_effect = ["我是一句話，這是第二句。", "最後一句了！"]
        
        result = auto_postprocess.format_text_with_ai(sentences)
        
        self.assertEqual(mock_call_api.call_count, 2)
        
        # 驗證段落之間是否有兩個換行
        expected_result = "我是一句話，這是第二句。\n\n最後一句了！"
        self.assertEqual(result, expected_result)

    @patch('requests.post')
    def test_e2e_punctuation_api_call(self, mock_post):
        """E2E 端到端測試：模擬真實 requests 呼叫回傳，驗證 ResilientAPIClient 整合"""
        # 初始化一份獨立的 client，用來確保 model 是 2.5 flash
        test_client = ResilientAPIClient(
            api_base_url="http://test.url",
            api_key="test_key",
            model="gemini-2.5-flash",
            base_delay=0.1 # 縮短測試延遲
        )
        
        # 暫時替換掉 auto_postprocess 內部的 client
        with patch('auto_postprocess._api_client', test_client):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "這是加上標點符號的結果。"
                    }
                }]
            }
            mock_post.return_value = mock_response

            sentences = ["這", "是", "測", "試"]
            result = auto_postprocess.format_text_with_ai(sentences)

            self.assertEqual(result, "這是加上標點符號的結果。")
            
            # 檢查傳送出去的 model 參數是否為 gemini-2.5-flash
            call_args = mock_post.call_args
            self.assertIsNotNone(call_args)
            _, kwargs = call_args
            payload = kwargs.get('json', {})
            self.assertEqual(payload.get('model'), "gemini-2.5-flash")

if __name__ == '__main__':
    unittest.main()

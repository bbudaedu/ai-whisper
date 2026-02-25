# 任務：修復 YouTube 影片重複處理的問題 (ZJFFUHW_e4c)

## 目標
解決影片「佛教公案選集 簡豐文居士 012」處理完成後，`auto_youtube_whisper.py` 腳本沒有正確更新 `processed_videos.json`，導致下一次 cron 執行時又重複處理同一部影片的問題。

## 方案與執行
1. **排查錯誤日誌**：查看了 `auto_youtube_whisper_cron.log` 中的運行情況，發現腳本在寄出 Email 之後拋出了 `TypeError: list indices must be integers or slices, not str`。
2. **分析根因**：問題在於 `processed_videos.json` 目前儲存的是一個陣列（List），例如 `["m4IucOsOZhQ", "zOBbKf8gt1g", "keoeMspJAcU"]`，但在 `auto_youtube_whisper.py` 中，程式試圖以字典的方式去賦值：`processed[video["id"]] = {...}`。這個型別不符導致腳本閃退，所以它永遠無法更新並儲存檔案。
3. **修復腳本**：修改 `auto_youtube_whisper.py` 裡的 `load_processed_videos` 函數，當它發現載入的資料是 List 時，自動轉換為 Dictionary 格式，防禦 TypeError 問題。
4. **修復狀態檔案**：由於當前背景執行的腳本正在進行 Gemini 校對，且當初掛載的舊列表結構必然會讓它執行到尾端時死機，因此手動先將 `ZJFFUHW_e4c` 的紀錄寫入 `processed_videos.json`，以確保等一下 11:00 cron 執行時絕不會再次處理這部影片。

## 狀態
- [x] 修復 TypeError (由 List 與 Dictionary 不兼容引起)
- [x] 修改 `auto_youtube_whisper.py`
- [x] 更新 `processed_videos.json` 包含 `ZJFFUHW_e4c` 
- [x] 完成本次 Debug 任務

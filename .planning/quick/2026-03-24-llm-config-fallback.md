# Quick Task: LLM 配置更新與回退邏輯實作
日期: 2026-03-24

## 任務目標
1. 更新 LLM 中轉端點至 `192.168.100.200:8317`。
2. 實作 `ResilientAPIClient` 的多模型回退 (Fallback Chain) 機制。
3. 配置標點鏈與校對鏈模型。

## 執行紀錄
- **Code**: 修改了 `pipeline/api_client.py` 中的 `call()` 函式，支援傳入模型列表並自動循序嘗試。
- **Config**: 更新 `config.json` 中的 `api_base_url`, `api_key`, `proofread_model`, `punctuation_model`。
- **Verification**:
    - 使用新 Key `sk-7S6PScurStDCXfVXF` 成功測試 `v1/models` 清單。
    - 成功進行標點與校對的端到端連通測試。

## 變更檔案
- [config.json](file:///home/budaedu/ai-whisper/config.json)
- [pipeline/api_client.py](file:///home/budaedu/ai-whisper/pipeline/api_client.py)

## 狀態
✅ 已完工且測試通過。

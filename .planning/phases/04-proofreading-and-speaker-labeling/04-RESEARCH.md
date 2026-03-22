# Phase 04: 校對增強與說話者標註 - 研究

**研究日期:** 2026-03-22
**領域:** 自然語言處理（NLP）、語音轉文字（ASR）、說話者分類（Speaker Diarization）、大型語言模型（LLM）
**信心:** HIGH

## 摘要

本階段旨在提升系統的 transcription 品質，透過導入「說話者分離（Speaker Diarization）」與「LLM 輔助校對」功能。目標是將原始的語音轉錄結果轉換為具備說話者識別與精確內容的文本，並支援使用者上傳參考文件來提升 LLM 校對的上下文準確度。

**主要建議:** 優先實作 Speaker Diarization 模型整合（如 Pyannote.audio），並建立基於 RAG 或上下文注入的 LLM 校對流水線。

## 標準技術棧

### 核心 (Transcription & Diarization)
| 套件 | 版本 | 用途 | 為什麼標準 |
| :--- | :--- | :--- | :--- |
| `pyannote.audio` | 3.1+ | 說話者分離 | 業界標準，開源且準確度高 |
| `faster-whisper` | 1.0+ | 語音轉錄 | 效能優化，適合處理長音檔 |

### 支援 (LLM 校對)
| 套件 | 版本 | 用途 | 使用時機 |
| :--- | :--- | :--- | :--- |
| `langchain` | 0.3+ | 鏈式處理 | 管理 Prompt 與 LLM 對話邏輯 |
| `pydantic` | 2.0+ | 資料結構化 | 確保 LLM 校對輸出格式一致 |

### 替代方案考慮
| 取代 | 替代方案 | 取捨 |
| :--- | :--- | :--- |
| `pyannote` | `WhisperX` | WhisperX 整合了 Whisper 與 Diarization，部署更簡單，但靈活性較低 |

**安裝:**
```bash
pip install pyannote.audio faster-whisper langchain pydantic
```

## 架構模式

### 建議專案結構
```
pipeline/
├── diarization/      # 說話者分離邏輯
├── proofreading/     # LLM 校對與參考文件邏輯
└── tasks/            # 整合轉錄、分離、校對的工作流
```

### 模式 1: Speaker Diarization 流程
1. **轉錄:** 先使用 `faster-whisper` 取得時間戳與文本。
2. **分離:** 使用 `pyannote.audio` 對相同音檔進行說話者區段標記。
3. **對齊:** 將轉錄文本與說話者區段的時間戳進行對齊（Alignment）。

### 反模式 (Anti-Patterns)
- **直接將整段文本丟給 LLM 進行校對:** 若無參考文本，容易出現幻覺（Hallucination），應分段處理或注入上下文。
- **過於依賴單一模型準確度:** Diarization 在重疊發言時準確度會下降，需保留原始時間戳與信心分數。

## 不要自行實作 (Don't Hand-Roll)

| 問題 | 不要自己做 | 請使用 | 為什麼 |
| :--- | :--- | :--- | :--- |
| 說話者分段 | 手動根據音量切割 | `pyannote.audio` | 處理語音重疊與語者判斷太複雜 |
| 格式對齊 | 手動解析時間戳 | `WhisperX` 或 `pydantic` 結構化 | 避免維護複雜的 Regex 或字串切割 |

## 常見陷阱

### 陷阱 1: GPU 記憶體爆掉
**發生狀況:** 同時載入 Whisper 模型與 Pyannote 模型。
**預防策略:** 採用 Pipeline 分階段載入，或利用 `Faster-Whisper` 節省的資源配置給 Diarization。

### 陷阱 2: LLM 參考文件過大
**發生狀況:** 使用者上傳的講義內容過長，超過 Token 限制。
**預防策略:** 實作簡單的 RAG（檢索增強生成），僅擷取與該片段相關的參考內容注入 Prompt。

## 程式碼範例

### 說話者標註流程 (概念)
```python
# 來源: pyannote.audio 文件範例
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
diarization = pipeline("audio.wav")

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
```

## 開放問題

1. **說話者名稱持久化 (PROC-03):** 現階段僅標註 A/B/C，後續需考慮如何儲存對應的真實姓名。
   - 建議: 在 DB 中建立 `SpeakerProfile` 資料表，與 `Task` 關聯。
2. **參考文件管理 (PROC-05):** 使用者上傳講義的權限與存取範圍。
   - 建議: 預設為使用者私有，僅在特定 Task 勾選時加載。

## 驗證架構

### 測試框架
- **框架:** `pytest`
- **架構:** 針對 `pipeline/diarization` 與 `pipeline/proofreading` 編寫單元測試。

### 相位需求 -> 測試地圖
| 需求 ID | 行為 | 測試類型 | 自動化命令 |
| :--- | :--- | :--- | :--- |
| PROC-03 | 說話者分類 | 單元測試 | `pytest tests/test_diarization.py` |
| PROC-04 | LLM 校對輔助 | 整合測試 | `pytest tests/test_proofreading.py` |
| PROC-05 | 講義資料庫讀取 | 單元測試 | `pytest tests/test_lecture_db.py` |

## 來源

### 主要 (HIGH confidence)
- [pyannote.audio documentation](https://github.com/pyannote/pyannote-audio) - 說話者分離標準實現
- [Faster-Whisper documentation](https://github.com/SYSTRAN/faster-whisper) - 轉錄效能優化

### 次要 (MEDIUM confidence)
- [LangChain RAG concepts](https://python.langchain.com/) - LLM 參考文本注入模式

## 元數據

**信心分析:**
- 標準技術棧: HIGH - 業界常見且有明確實作規範
- 架構: MEDIUM - 需考慮 GPU 資源限制
- 陷阱: HIGH - GPU 記憶體與 Context Window 是常見痛點

**研究日期:** 2026-03-22
**有效期限:** 30 天

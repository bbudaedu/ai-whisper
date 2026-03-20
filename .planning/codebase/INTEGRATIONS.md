# 外部整合（Integrations）

**Analysis Date:** 2026-03-20

## 外部服務 / API

- **NotebookLM**
  - 相關程式：`auto_notebooklm.py`, `pipeline/notebooklm_client.py`, `pipeline/notebooklm_scheduler.py`, `pipeline/notebooklm_tasks.py`
  - 可能透過 API/自動化流程與 NotebookLM 互動。

- **YouTube / Whisper 流程**
  - 相關程式：`auto_youtube_whisper.py`
  - 相關產出：`*.srt`, `*.vtt`, `*.tsv`, `*.txt`

## 狀態/資料儲存

- **JSON 檔案作為狀態儲存**
  - `notebooklm_queue.json`
  - `processed_videos.json`

## 檔案/資料來源

- NAS/掛載路徑：`mnt/`（例如 `mnt/nas/`）
- 產出與記錄：`*.log`, `*.lock`

## 設定與憑證

- 設定集中於 `config.json`（可能包含 API key 或敏感設定；未展開驗證）

---

*Integrations analysis: 2026-03-20*

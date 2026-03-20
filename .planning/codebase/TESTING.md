# 測試概況（Testing）

**Analysis Date:** 2026-03-20

## 測試框架

- **pytest**（Python）

## 測試目錄與檔案

- 主要測試目錄：`tests/`
- 代表性測試：
  - `tests/test_notebooklm_tasks.py`
  - `tests/test_notebooklm_client.py`
  - `tests/test_notebooklm_scheduler.py`
  - `tests/test_notebooklm_tasks.py`
  - `tests/test_e2e_pipeline.py`

## 測試型態

- **Unit tests**：`pipeline/notebooklm_tasks.py` 等核心邏輯
- **E2E tests**：`tests/test_notebooklm_e2e.py`, `tests/test_e2e_pipeline.py`

## 測試寫法

- 使用 `pytest` 內建 `assert`
- 使用 `tmp_path` fixture 進行檔案/路徑測試
- 以 class 分組測試（例：`TestBuildPrompt`, `TestParseResponse`）

## 執行方式

```bash
pytest
pytest tests/test_notebooklm_tasks.py
```

---

*Testing analysis: 2026-03-20*

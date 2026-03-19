# SPEC: NotebookLM 後製功能完善

## 1. 概述

本專案目標為升級 `ai-whisper` 的 NotebookLM 後製管線，使其能將校對完成的 `.docx` 文件**直接上傳為筆記本來源（Source）**，並利用 NotebookLM Studio 原生功能產出多媒體輸出。

### 現有問題

- 僅將文本截斷至 4000 字後貼入聊天 → 品質與上下文不完整
- 無法觸發 Studio 原生功能（Audio Overview、Mind Map 等）因筆記本內無來源
- `notebooklm-mcp` 第三方 MCP Server 不支援檔案上傳

### 目標架構

```
校對完成 (.docx) → 自動建立筆記本 → 上傳 .docx 為 Source → Studio 產出 → 儲存結果
                                                              ↓ (超過限額時)
                                                       LRU 刪除最舊筆記本
```

## 2. 關鍵決策

| 項目 | 決策 |
|------|------|
| 筆記本策略 | **每集獨立筆記本**，超過上限時 LRU 刪除最舊的 |
| 產出方式 | **NotebookLM Studio 原生功能**（Audio Overview、Mind Map、Presentation 等） |
| 技術路線 | **Fork `notebooklm-mcp`** 增加 `create_notebook`、`upload_source`、`delete_notebook` 工具 |
| 配額策略 | **佇列依序產出**，每日用完免費額度自動暫停，隔日繼續 |

## 3. 功能需求

### 3.1 MCP Server 擴充（Fork `notebooklm-mcp`）

| 新工具 | 參數 | 行為 |
|--------|------|------|
| `create_notebook` | `name: string` | 建立新筆記本，返回 `notebook_url` |
| `upload_source` | `notebook_url, file_path, file_type` | 上傳本地檔案為筆記本來源 |
| `delete_notebook` | `notebook_url` | 刪除指定筆記本 |
| `list_sources` | `notebook_url` | 列出筆記本內的來源 |

瀏覽器自動化策略：
- 使用現有 Patchright (stealth Playwright) + SharedContextManager
- NotebookLM UI 操作：檔案上傳按鈕 → file chooser API → 等待處理完成

### 3.2 Python Pipeline 更新（`ai-whisper`）

#### `notebooklm_client.py` 新增方法
- `create_notebook(name) → notebook_url`
- `upload_source(notebook_url, file_path) → bool`
- `delete_notebook(notebook_url) → bool`
- `list_sources(notebook_url) → list`

#### `notebooklm_scheduler.py` 新增生命週期管理
- 每集處理前：建立筆記本 → 上傳 .docx
- 每集處理後：記錄筆記本 URL 至 metadata
- 超過筆記本上限時：LRU 刪除最舊的（含 MCP 刪除 + 本地清理）

#### `notebooklm_tasks.py` 更新
- 移除 prompt-based `ask_question` 產出（MINDMAP、PRESENTATION 等）
- 改為 Studio 原生工具呼叫

#### `auto_notebooklm.py` 更新
- 新增 `.docx` 檔案定位邏輯（NAS 目錄掃描）
- 整合筆記本生命周期管理

### 3.3 筆記本限額管理

- 維護 `notebooklm_notebooks.json`：記錄每個筆記本的建立時間、URL、關聯 episode
- 可設定上限（例如 100 本），超過時 LRU 刪除
- 刪除前先透過 MCP `delete_notebook` 清除雲端

## 4. 非功能需求

- **冪等性**：重複執行不應重複上傳或建立筆記本
- **錯誤恢復**：上傳失敗時標記 FAILED，不阻塞後續任務
- **日誌**：所有操作記錄至 stdout（Systemd 捕獲）
- **配額安全**：每日額度用盡自動暫停，不會觸發帳號風險

## 5. 範圍外

- 多帳號輪替（未來增強）
- 前端 UI（沿用現有 Dashboard）
- NotebookLM Plus/Enterprise 整合

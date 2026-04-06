# Phase 5: 長期保存與歷史查詢 - Research

**Researched:** 2026-03-23
**Domain:** Persistence, Archiving, Task History
**Confidence:** HIGH

<user_constraints>
## User Constraints (from 05-CONTEXT.md)

### Locked Decisions
- **D-01:** 採取永久保留策略，任務紀錄、原始輸入音檔、轉錄輸出與衍生成果不主動清理或刪除。
- **D-02:** 長期保存的核心對象為「任務」而不是「單集 Notebook」，資料模型必須以 task/job 為主體。
- **D-03:** 必須同時覆蓋外部使用者提交的任務，以及既有內部工作流產生的任務，並維持內部優先的既有排程規則不變。
- **D-04:** 必須保存 `task_id`、`owner/user_id`、`source_type`（upload / youtube / playlist-detected）、`audio_profile`（會議 / 佛學課程）、建立時間、完成時間、狀態、重試次數與錯誤訊息。
- **D-05:** 必須保存任務的輸入來源資訊，例如原始檔名、儲存路徑或物件鍵、YouTube URL、playlist subscription 關聯與觸發方式。
- **D-06:** 必須保存任務輸出成果資訊，包括可下載檔案清單、格式（txt / srt / vtt / tsv / json / word / excel）、檔案路徑或物件鍵、產生時間與可用狀態。
- **D-07:** 必須保存可供歷史查詢的流程事件，例如 pending、running、done、failed、cancelled 與各 stage 的時間點，供 UI 與 API 顯示歷程。
- **D-08:** Phase 5 的主要使用面為既有 FastAPI 與外部 Web UI 的歷史查詢與下載能力，不以 CLI 作為主要交付介面。
- **D-09:** 外部使用者只能查詢與下載自己擁有或被授權的任務與檔案；內部使用者則依既有管理權限查看。
- **D-10:** 歷史任務必須可依任務狀態、建立時間、來源類型與關鍵字查詢，至少支援列表、詳情與結果下載三種基本操作。
- **D-11:** 關聯式中繼資料可使用 SQLite 作為 v1 落地方案，但 schema 必須圍繞 FaYin task 與 artifact 設計，而非 episode/notebook 結構。
- **D-12:** 檔案保存層需與資料庫中繼資料明確對應，避免只有紀錄沒有實體檔案，或有檔案但無法追蹤來源與擁有者。
- **D-13:** 若沿用 SQLite，需考慮併發寫入時的 timeout、transaction 邊界與單寫入序列化策略，以降低 database locked 風險。

### Claude's Discretion
- SQLite schema 的具體表結構與索引設計。
- 長期保存檔案的實體路徑規劃。
- 歷史列表與詳情 API 的分頁、排序與篩選參數。
- 外部 Web UI 歷史頁面的資訊密度與下載入口呈現方式。

### Deferred Ideas (OUT OF SCOPE)
- 全文檢索與進階搜尋條件。
- 管理員跨使用者統計報表。
- 分層儲存、冷資料歸檔與未來可能的保留政策調整。
- 額外的 CLI 匯出或靜態報表功能。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-01 | 音檔與輸出成果永久保留 | D-01, D-05, D-06, D-12 |
| STOR-02 | 任務紀錄永久保存 | D-02, D-04, D-07, D-11 |
</phase_requirements>

## Summary

本階段重點在於將 FaYin 的任務生命週期延伸為「永久性紀錄」。核心策略是建立以 `task` 為中心的 SQLite schema，將過去分散的檔案與狀態資訊收攏為關聯式結構，確保輸入源、處理歷程與產出成果可被明確追蹤與存取。

**Primary recommendation:** 優先擴充現有 FastAPI 的 `tasks` 相關邏輯，在任務處理的關鍵生命週期節點（建立、狀態轉移、結果產出）強制寫入 `tasks`、`task_events` 與 `task_artifacts` 表格，並確保檔案存儲路徑與資料庫中 `artifact_path` 對應關係的嚴謹性。

## Standard Stack

### Core
| Library | Purpose | Why Standard |
|---------|---------|--------------|
| `sqlite3` | 關聯式儲存 | 符合 D-11，輕量且足以承載中繼資料 |
| `pydantic` | 資料結構驗證 | 確保任務與事件模型的資料完整性 |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `pathlib` | 檔案路徑管理 | 處理長期保存檔案的實體路徑規劃 |

## Architecture Patterns

### Recommended Project Structure
```
data/
├── tasks/           # 任務原始輸入與轉錄結果根目錄
│   ├── {task_id}/   # 單一任務隔離資料夾
│   │   ├── raw/     # 原始音檔
│   │   └── results/ # 處理後成品
```

### Pattern 1: Event-Driven Persistence
**What:** 在任務處理的每個階段（Stage Change）同步更新 `task_events` 與 `tasks` 狀態。
**When to use:** 所有任務狀態變更時。
**Example:**
```python
# 範例邏輯
def log_task_event(task_id: str, event_type: str, metadata: dict = None):
    # 寫入 sqlite task_events 表
    pass
```

### Anti-Patterns to Avoid
- **檔案未記錄化:** 直接將檔案存入路徑而不寫入 `task_artifacts` 表格，導致後續無法追蹤擁有者與關聯。
- **過度正規化/非正規化:** 依據 `database-design` 技能，對於讀取頻繁但變更極少的歷史狀態資訊，應保持適度的非正規化以加速查詢。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 並發寫入 SQLite | custom mutex locking | Connection Pooling/WAL mode | 使用 SQLite WAL mode 可有效緩解併發寫入帶來的 database locked 問題 |

**Key insight:** 長期保存的關鍵不在於技術選型，而在於「metadata 對於物理檔案的約束力」。

## Common Pitfalls

### Pitfall 1: SQLite Database Locked
**What goes wrong:** 多個任務 stage 同時更新狀態導致寫入衝突。
**Why it happens:** SQLite 預設的寫入序列化行為。
**How to avoid:** 啟用 WAL (Write-Ahead Logging) mode，並在應用層確保事務邊界清晰。
**Warning signs:** `sqlite3.OperationalError: database is locked`.

## Code Examples

Verified patterns for persistence:

### Artifact Registration
```python
# 註冊產出檔案
def register_artifact(task_id: str, format: str, path: str):
    # INSERT INTO task_artifacts (task_id, format, path, created_at)
    # VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    pass
```

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — 既有任務執行紀錄零散 | 需要實作新 Schema 並完成舊有任務紀錄匯入邏輯 |
| Live service config | None — 依據 D-11/12 需要明確路徑對應 | 設計路徑對應規則 (D-40) |
| OS-registered state | None | N/A |
| Secrets/env vars | None | N/A |
| Build artifacts | None | N/A |

## Open Questions

1. **舊有任務匯入策略**
   - 若要保存歷史，現有系統中的既有未完成或已完成任務是否需要補寫入新 Schema？建議實作一個 migration script 進行資料掃描與補正。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` |
| Quick run command | `pytest tests/test_persistence.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| STOR-01 | 音檔與結果保存 | integration | `pytest tests/test_persistence.py::test_artifact_persistence` |
| STOR-02 | 任務紀錄保存 | unit | `pytest tests/test_persistence.py::test_task_event_logging` |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/05-long-term-history/05-CONTEXT.md` - Phase 5 核心需求與決策
- `.planning/REQUIREMENTS.md` - 專案核心需求
- `.agent/skills/database-design/` - 資料庫設計原則

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 基於既有 SQLite 體系
- Architecture: HIGH - 圍繞 Task 中心化設計
- Pitfalls: HIGH - WAL 模式為標準建議

**Research date:** 2026-03-23
**Valid until:** 2026-04-22

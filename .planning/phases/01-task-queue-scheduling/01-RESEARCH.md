# Phase 1: 任務佇列與排程基礎 - Research

**Researched:** 2026-03-21
**Domain:** Task queue & scheduling（FastAPI + SQLite + SQLModel）
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### 佇列持久化策略
- 使用 SQLite 作為任務佇列的持久化層，零外部依賴，適合單機環境
- 使用輕量 ORM（SQLModel）管理資料模型，與 FastAPI + Pydantic 自然整合
- 任務狀態模型：`pending → running → done / failed`，與 ROADMAP.md 定義的 API 查詢狀態一致
- 現有 `processed_videos.json` 採漸進遷移：新任務寫入 SQLite，舊資料按需讀取 JSON fallback，確保不破壞現有功能

### 排程與優先權機制
- 佇列分級：內部佇列先清空再處理外部佇列，實現內部任務優先
- 排程觸發方式：Polling loop（固定間隔檢查佇列），沿用現有 `auto_youtube_whisper.py` 的 loop 模式
- 保留現有 `gpu_lock.py` 的 `fcntl.flock` 機制，排程器取得佇列鎖後再嘗試 GPU lock
- 排程器以 FastAPI 背景任務（asyncio task）運行，整合至現有 API server

### Pipeline Stage 並行策略
- 每個 stage 是獨立任務，完成後自動排入下一 stage（下載→聽打→校對→排版）
- 父任務 + 子任務模型：播放清單任務為父，每集為子任務，便於查詢整體進度
- 下載限制 2 並行（沿用現有 `dl_semaphore` 模式），校對/排版不設並行限制
- 現有 `auto_youtube_whisper.py` 核心邏輯抽取為 pipeline 模組，原腳本保留作為 CLI 入口

### 失敗與重試行為
- 指數退避重試，預設 3 次
- 任務層級的 `max_retries` 欄位，可依任務設定重試次數
- 僅重試失敗的 stage，不重新執行已完成的 stage
- 任務記錄重試次數（`retry_count`）與最後錯誤訊息（`error_message`），狀態為 `failed` 時帶錯誤資訊

### Claude's Discretion
- SQLite 資料表結構的具體設計（欄位命名、索引策略）
- Polling 間隔的具體秒數
- 指數退避的具體參數（base delay、max delay）
- 日誌格式與 structured logging 的具體方案
- 單元測試的具體框架選擇（pytest vs unittest）
- Pipeline 模組的檔案組織結構

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. All queue/scheduling decisions are scoped to Phase 1 requirements (QUEUE-01 through QUEUE-05).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUEUE-01 | 系統提供異步任務佇列，任務提交後排隊等待 GPU 資源 | SQLite + SQLModel 佇列持久化、狀態流轉與排程模式（Polling loop + 原子 claim） |
| QUEUE-02 | 單 GPU 排程機制，一次只執行一個 Whisper 任務 | `gpu_lock.py` + 佇列內部鎖 + 排程器單一 running 任務規則 |
| QUEUE-03 | 內部任務優先於外部任務執行 | 兩級佇列（internal/external）與排序策略 + 索引設計 |
| QUEUE-04 | 工作流模組化為獨立 stage（下載→聽打→校對→排版），各 stage 可並行 | 父子任務/Stage 任務模型 + stage 完成自動 enqueue 下一 stage |
| QUEUE-05 | 失敗任務自動重試（可設定重試次數） | Retry 欄位、指數退避策略、僅重試失敗 stage 的狀態模型 |
</phase_requirements>

## Summary

本階段必須在「單機、單 GPU、不可破壞既有流程」前提下，把現有腳本式流程改造成可持久化的任務佇列與分段排程。已鎖定使用 SQLite + SQLModel 作為持久化層，FastAPI 內部以 Polling loop + asyncio task 執行排程，並透過 `gpu_lock.py` 確保 GPU 互斥。核心設計重點是：**可重啟、可恢復、且狀態可查**，並且在 Stage 成功後立即推進下一 Stage，以滿足「第 1 集完成下載即可進入聽打」的並行需求。

依照現有程式碼，NotebookLM 佇列已具備「持久化 + 狀態流轉 + 順序執行」模式，可作為設計參考，但本階段要在 SQLite 中提供更可靠的狀態與查詢。SQLite 併發要點包含 WAL 模式、busy timeout 與 `check_same_thread` 設定，避免 FastAPI 背景任務與 API 同時存取導致鎖衝突。FastAPI 背景任務不適合長時間排程主迴圈，建議採用 lifespan 啟動/關閉 scheduler，以避免 request lifecycle 影響排程。

**Primary recommendation:** 以 SQLite + SQLModel 建立「任務 / stage / 嘗試」最小可用 schema，使用原子更新 claim 任務，並在 FastAPI lifespan 啟動 Polling scheduler（搭配 `gpu_lock.py`），確保單 GPU 與內部優先權可被一致落實。

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLite | builtin | 單機持久化佇列 | 零外部依賴、符合單機環境與 Phase 1 需求 |
| SQLModel | 0.0.37 (2026-02-21) | ORM + 型別模型 | 與 FastAPI/Pydantic 整合自然，降低模型與資料庫耦合 |
| SQLAlchemy | 2.0.48 (2026-03-02) | DB 引擎/連線層 | SQLModel 底層引擎，SQLite 連線與 pooling 行為可控 |
| FastAPI | 0.135.1 (2026-03-01) | API server / 背景排程 | 現有後端基礎，支援 lifespan 與背景流程 |
| Pydantic | 2.12.5 (2025-11-26) | 資料驗證 | FastAPI 預設驗證層 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | repo-managed | 測試框架 | 佇列、排程、重試、stage 流程測試 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite + SQLModel（locked） | raw sqlite3 | 需手動管理 schema/交易與型別，維護成本高（不符已決策） |

**Installation:**
```bash
pip install fastapi sqlmodel sqlalchemy pydantic
```

**Version verification:** 已透過 PyPI 官方頁面確認版本與發布日期（見 Sources）。

## Architecture Patterns

### Recommended Project Structure
```
pipeline/
├── queue/
│   ├── models.py          # SQLModel: Task, StageTask, Attempt
│   ├── repository.py      # DB 存取/交易與原子 claim
│   ├── scheduler.py       # Polling loop + 優先權 + GPU lock
│   ├── stage_runner.py    # stage 執行器（下載/聽打/校對/排版）
│   └── backoff.py         # 指數退避與 retry 計算
└── stages/
    ├── download.py
    ├── transcribe.py
    ├── proofread.py
    └── postprocess.py
```

### Pattern 1: 兩層任務模型（父任務 + Stage 子任務）
**What:** 父任務表示「播放清單或外部任務」，子任務表示每一集/每個 stage 的實際工作；子任務完成後 enqueue 下一 stage。
**When to use:** 需要同時追蹤整體進度與單集進度，且支援 stage 並行時。
**Example:** 父任務建立後，為每集建立 `download` 子任務；完成後自動新增 `transcribe` 子任務。

### Pattern 2: 原子 claim（避免雙重執行）
**What:** 用單一 SQL update 原子地把 `pending` 轉成 `running`，避免多 worker 競爭時重複執行。
**When to use:** Polling loop 內部嘗試取得下一個可執行任務時。
**Example:** `UPDATE stage_tasks SET status='running' ... WHERE id = (SELECT id ... LIMIT 1) AND status='pending'`，依 rowcount 決定是否成功 claim。

### Pattern 3: Lifespan 啟動排程器
**What:** 使用 FastAPI `lifespan` 啟動 `asyncio.create_task` 的 scheduler loop，並在 shutdown 時取消。
**When to use:** 需要背景長時間執行排程，且不應綁定在單一 request。
**Example:** 於 lifespan startup 內建立 scheduler task，保存 reference，shutdown 取消。

### Anti-Patterns to Avoid
- **在 API handler 內啟動長時間排程器：** `BackgroundTasks` 僅適合短任務，會被 request lifecycle 影響。
- **以 in-memory queue 取代 SQLite：** 無法容錯重啟、也不符合持久化需求。
- **任務重試重跑全部 stage：** 會破壞已完成輸出並浪費 GPU 時間。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GPU 互斥 | 自行寫新的鎖檔/IPC | 既有 `gpu_lock.py` | 已部署於現有流程，確保相容性 |
| 佇列持久化 | 自行設計 JSON 檔案隊列 | SQLite + SQLModel | 支援交易與查詢，可靠性高 |
| 多執行緒 SQLite 連線 | 自訂 thread-safe wrapper | SQLAlchemy `connect_args` 設定 | 官方支援 `check_same_thread` 行為 |
| 背景任務框架 | 自訂 daemon 或 cron | FastAPI lifespan + asyncio task | 與現有 API server 整合，部署成本低 |

**Key insight:** 這個階段的可靠性來自「持久化 + 原子狀態轉換 + 既有 GPU lock」，不要把可靠性建立在易遺失的記憶體與手寫同步邏輯上。

## Common Pitfalls

### Pitfall 1: SQLite BUSY/鎖衝突
**What goes wrong:** scheduler 或 API 同時操作 SQLite，遇到 `SQLITE_BUSY` 導致任務無法 claim。
**Why it happens:** WAL 模式或 busy timeout 未設定，或 DB 放在不支援 WAL 的檔案系統。
**How to avoid:** 啟用 WAL 模式、設定 busy timeout，並確保 DB 在本機磁碟（避免 NAS）。
**Warning signs:** 日誌頻繁出現 busy 或鎖競爭訊息。

### Pitfall 2: `check_same_thread` 例外
**What goes wrong:** FastAPI 背景任務使用 SQLModel/SQLAlchemy 時拋出 `SQLite objects created in a thread can only be used in that same thread`。
**Why it happens:** SQLite 預設限制連線只能在建立它的 thread 使用。
**How to avoid:** 使用 SQLAlchemy `connect_args={"check_same_thread": False}`（檔案型 DB）。
**Warning signs:** API 路由正常、背景排程讀寫失敗。

### Pitfall 3: BackgroundTasks 被誤用為長時間排程
**What goes wrong:** 排程 loop 被 request lifecycle 中斷或無法穩定運行。
**Why it happens:** FastAPI `BackgroundTasks` 只適合短任務，不適合長時程排程。
**How to avoid:** 使用 FastAPI lifespan + `asyncio.create_task` 保持長時程排程器。
**Warning signs:** 排程器只在特定 request 後執行或突然停止。

### Pitfall 4: 重試策略重跑完成階段
**What goes wrong:** 已完成的 stage 被重跑，導致結果被覆寫或產生不一致輸出。
**Why it happens:** 缺少 stage 等級的狀態欄位或 retry 狀態。
**How to avoid:** 對每個 stage 記錄狀態與 retry_count，僅重試失敗 stage。
**Warning signs:** 重試後輸出檔案被覆蓋、處理時間暴增。

## Code Examples

Verified patterns from official sources:

### SQLModel: create engine + create tables
```python
from sqlmodel import SQLModel, create_engine

engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)
```
Source: https://sqlmodel.tiangolo.com/tutorial/create-db-and-table/

### SQLModel: Session insert
```python
from sqlmodel import Session

with Session(engine) as session:
    session.add(hero_1)
    session.add(hero_2)
    session.commit()
```
Source: https://sqlmodel.tiangolo.com/tutorial/insert/

### FastAPI Lifespan (startup/shutdown)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

app = FastAPI(lifespan=lifespan)
```
Source: https://fastapi.tiangolo.com/advanced/events/

### FastAPI BackgroundTasks (短任務)
```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

def write_notification(email: str, message=""):
    with open("log.txt", mode="w") as email_file:
        email_file.write(f"notification for {email}: {message}")

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_notification, email, message="some notification")
    return {"message": "Notification sent in the background"}
```
Source: https://fastapi.tiangolo.com/tutorial/background-tasks/

### SQLAlchemy SQLite thread config
```python
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```
Source: https://docs.sqlalchemy.org/21/dialects/sqlite.html

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `processed_videos.json` + subprocess 觸發 | SQLite 佇列 + in-process scheduler | Phase 1 計畫（2026-03） | 可持久化、可查詢、可重啟 |
| 單一腳本循環 | stage 任務分解 + 並行下載 | Phase 1 計畫（2026-03） | 縮短整體等待時間 |

**Deprecated/outdated:**
- 以 JSON 檔案做任務佇列：缺乏交易與一致性，不適合排程與重試。

## Open Questions

1. **SQLite 檔案位置**
   - What we know: 需要避免 NAS/網路檔案系統，以免 WAL 失效。
   - What's unclear: DB 應放在專案根目錄或獨立 data 目錄？
   - Recommendation: 明確指定本機路徑並在啟動時檢查可寫。

2. **Polling interval 與 backoff 參數**
   - What we know: Polling 模式已鎖定。
   - What's unclear: interval 秒數、base delay / max delay。
   - Recommendation: 先用保守值（例如 3-5 秒、max 60 秒），再用實測調整。

3. **Schema 索引策略**
   - What we know: 需要 internal/external 佇列優先、status 查詢。
   - What's unclear: composite index 的欄位排序（priority, created_at, status）。
   - Recommendation: 以 `status + priority + created_at` 為基本索引，觀察查詢成本後再調整。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (repo現有) |
| Config file | none — see Wave 0 |
| Quick run command | `pytest -q` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUEUE-01 | 任務提交後進入 pending，且可被排程 claim | integration | `pytest -q tests/test_task_queue.py::test_enqueue_pending` | ❌ Wave 0 |
| QUEUE-02 | 單 GPU 只允許一個 running 任務 | unit | `pytest -q tests/test_scheduler_gpu_lock.py::test_single_gpu_enforced` | ❌ Wave 0 |
| QUEUE-03 | 內部任務優先於外部任務 | unit | `pytest -q tests/test_scheduler_priority.py::test_internal_before_external` | ❌ Wave 0 |
| QUEUE-04 | stage 完成後自動 enqueue 下一 stage | integration | `pytest -q tests/test_pipeline_stages.py::test_stage_fanout` | ❌ Wave 0 |
| QUEUE-05 | 失敗任務會重試且顯示 retry_count | unit | `pytest -q tests/test_retry_policy.py::test_retry_backoff` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -q`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_task_queue.py` — 佇列持久化與 pending/running 流程
- [ ] `tests/test_scheduler_gpu_lock.py` — GPU lock 互斥行為
- [ ] `tests/test_scheduler_priority.py` — 內部/外部優先權
- [ ] `tests/test_pipeline_stages.py` — stage fan-out 行為
- [ ] `tests/test_retry_policy.py` — retry/backoff 行為
- [ ] SQLite 測試 fixture（temp DB + Session）

## Sources

### Primary (HIGH confidence)
- https://sqlmodel.tiangolo.com/tutorial/create-db-and-table/ — SQLModel engine + create_all
- https://sqlmodel.tiangolo.com/tutorial/insert/ — SQLModel Session insert
- https://fastapi.tiangolo.com/advanced/events/ — lifespan 啟動/關閉
- https://fastapi.tiangolo.com/tutorial/background-tasks/ — BackgroundTasks 用法與限制
- https://docs.sqlalchemy.org/21/dialects/sqlite.html — SQLite thread/pooling 設定
- https://www.sqlite.org/wal.html — WAL 與 SQLITE_BUSY 行為
- https://pypi.org/project/sqlmodel/ — SQLModel 版本/日期
- https://pypi.org/project/sqlalchemy/ — SQLAlchemy 版本/日期
- https://pypi.org/project/fastapi/ — FastAPI 版本/日期
- https://pypi.org/project/pydantic/ — Pydantic 版本/日期

### Secondary (MEDIUM confidence)
- None

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 版本來自官方 PyPI
- Architecture: MEDIUM — 依現有程式碼與官方模式推導
- Pitfalls: MEDIUM — SQLite/FastAPI 官方文件支撐

**Research date:** 2026-03-21
**Valid until:** 2026-04-20

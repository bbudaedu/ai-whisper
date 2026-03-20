# Architecture Research

**Domain:** 語音處理平台（Whisper pipeline API 化 + 非同步任務佇列 + 外部 Web UI）
**Researched:** 2026-03-21
**Confidence:** MEDIUM（以專案既有架構與需求為主，未含外部權威來源）

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                Client Layer                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────┐ │
│  │ External Web UI App  │   │ Internal Dashboard   │   │ API Consumers     │ │
│  └───────────┬──────────┘   └───────────┬──────────┘   └──────────┬─────────┘ │
│              │                          │                         │           │
├──────────────┴──────────────────────────┴─────────────────────────┴───────────┤
│                                API Layer                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │ FastAPI: Auth + Task API + Upload + Status + Download + Webhook           │ │
│  └───────────────┬──────────────────────────────────────────────────────────┘ │
│                  │                                                              │
├──────────────────┴────────────────────────────────────────────────────────────┤
│                            Orchestration Layer                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐   ┌──────────────────────┐   ┌──────────────────────────┐  │
│  │ Task Registry │   │ Priority Queue/Bus   │   │ Scheduler/State Machine   │  │
│  └───────┬───────┘   └──────────┬──────────┘   └────────────┬──────────────┘  │
│          │                       │                          │                  │
├──────────┴───────────────────────┴──────────────────────────┴──────────────────┤
│                               Worker Layer                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐ │
│  │ Download      │  │ Transcribe    │  │ Proofread     │  │ Format/Export   │ │
│  │ (CPU/IO)      │  │ (GPU + lock)  │  │ (LLM/API)     │  │ (CPU)           │ │
│  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│                              Data/Storage Layer                               │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌──────────────────┐  ┌─────────────────────────────────┐ │
│  │ Task DB       │  │ File Storage     │  │ Logs/Events/Metadata            │ │
│  └───────────────┘  └──────────────────┘  └─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| External Web UI | 外部使用者上傳/追蹤/下載 | React + Vite + API client |
| Internal Dashboard | 內部監控與優先任務操作 | 既有 web-ui/ （保留） |
| API Layer | 認證、任務建立/查詢/取消、檔案上傳/下載、Webhook | FastAPI 路由層 |
| Task Registry | 任務狀態與階段資料來源 | RDB 或 Redis（Task 表） |
| Priority Queue | 任務排程（內部優先） | Redis queue / DB queue |
| Scheduler/State Machine | Pipeline stage 轉移、重試策略 | 背景 worker + 狀態機 |
| Download Worker | yt-dlp/ffmpeg 下載與轉檔 | CPU/IO worker |
| Transcribe Worker | faster-whisper + GPU lock | GPU single-flight worker |
| Proofread Worker | LLM 校對/標點 | API client worker |
| Format/Export Worker | 輸出格式生成 | CPU worker |
| Storage | 音檔/輸出檔永久保存 | 檔案系統或物件儲存 |

### Component Boundaries（Who talks to whom）

| Boundary | Communication | Notes |
|----------|---------------|-------|
| External UI ↔ API | REST/JSON | 不直接觸碰內部 pipeline 腳本 |
| Internal UI ↔ API | REST/JSON | 保持既有功能路徑 |
| API ↔ Task Registry | DB/ORM | API 只寫入任務與查詢狀態 |
| Scheduler ↔ Queue | enqueue/dequeue | 內部優先級策略落在此層 |
| Workers ↔ Storage | File/Blob IO | 所有檔案持久化保存 |
| Transcribe Worker ↔ GPU Lock | Lock/Mutex | 同時只允許一個轉錄任務 |

## Recommended Project Structure

```
api_server/
├── api/                    # FastAPI 路由（public + internal）
│   ├── external/           # 外部客戶端 API
│   ├── internal/           # 內部面板 API
│   └── deps.py             # auth/permissions
├── services/               # 任務建立、狀態查詢、通知
├── queue/                  # 佇列抽象與優先級策略
├── scheduler/              # 狀態機、重試、轉階段邏輯
├── workers/                # download/transcribe/proofread/format
├── pipelines/              # 現有腳本封裝為可重入的 task functions
├── models/                 # Task/Job/Asset 資料結構
├── storage/                # 檔案保存、路徑管理
└── notifications/          # webhook/email
web-ui/                      # 既有內部面板（保留）
web-ui-client/               # 外部客戶端 app（新）
shared/                      # API client + shared types（可選）
```

### Structure Rationale

- **api/**：清楚分離 external/internal API，避免外部需求影響內部面板行為。
- **queue/** 與 **scheduler/**：把「排程/狀態」獨立出來，確保 pipeline 可非同步運作且可重試。
- **workers/**：每個 stage 可獨立擴充與測試，不改動既有腳本時可用 wrapper 方式接入。
- **pipelines/**：包裝現有腳本，避免破壞既有內部流程（brownfield 安全邊界）。

## Architectural Patterns

### Pattern 1: Task State Machine（階段式狀態機）

**What:** 將任務拆成 download → transcribe → proofread → format，狀態明確可追蹤。
**When to use:** 非同步 pipeline、可中斷/重試、需要 UI 進度的系統。
**Trade-offs:** 增加狀態管理成本，但可測試性與可觀測性大幅提升。

**Example:**
```python
# 簡化示意
ALLOWED = {
    "queued": {"downloading"},
    "downloading": {"downloaded", "failed"},
    "downloaded": {"transcribing"},
    "transcribing": {"transcribed", "failed"},
    "transcribed": {"proofreading"},
    "proofreading": {"proofread", "failed"},
    "proofread": {"formatting"},
    "formatting": {"completed", "failed"},
}

def transition(task, new_state):
    if new_state not in ALLOWED.get(task.state, set()):
        raise ValueError("Invalid transition")
    task.state = new_state
```

### Pattern 2: Queue Handoff Between Stages（階段交接式佇列）

**What:** 每個 stage 完成後 enqueue 下一個 stage，而非同步 pipeline。
**When to use:** 需要並行下載 + 單 GPU 轉錄 + 後處理的場景。
**Trade-offs:** 需要可靠的 enqueue/ack 機制，避免重複執行。

**Example:**
```python
# 下載完成後觸發轉錄任務
queue.enqueue("transcribe", task_id=task.id, priority=task.priority)
```

### Pattern 3: GPU Single-Flight Lock（GPU 單工鎖）

**What:** 所有 GPU 任務必須取得鎖才能執行。
**When to use:** 單 GPU 環境，避免同時跑多個 Whisper 任務。
**Trade-offs:** 轉錄吞吐量受限，但避免資源競爭造成崩潰。

**Example:**
```python
with gpu_lock.acquire(timeout=...):
    run_faster_whisper(task)
```

## Data Flow

### Request Flow

```
外部使用者上傳/提交
    ↓
External UI → API (create task)
    ↓
Task Registry (state=queued)
    ↓
Priority Queue (internal first)
    ↓
Scheduler → Download Worker → Storage
    ↓
Scheduler → Transcribe Worker (GPU lock)
    ↓
Scheduler → Proofread Worker
    ↓
Scheduler → Format Worker → Storage
    ↓
API 通知 + External UI 查詢/下載
```

### State Management

```
Task DB
   ↑  ↓ (更新狀態/查詢)
Scheduler/Workers ↔ API
```

### Key Data Flows

1. **任務建立與排程**：API 寫入 Task → 佇列排序 → Scheduler 決定下一步。
2. **Pipeline 交接**：每個 stage 完成後更新狀態並 enqueue 下一個 stage。
3. **結果交付**：Storage 寫入輸出 → API 提供下載 → Webhook/Email 通知。

## Build Order Implications（建置順序建議）

1. **Task Registry + Priority Queue**：先建立任務資料模型與優先級排程規則（內部優先）。
2. **Scheduler/State Machine**：確保 pipeline 可以非同步前進，並可重試/取消。
3. **Worker Wrappers for Existing Pipeline**：以 wrapper 方式整合現有腳本，避免破壞原流程。
4. **API Layer**：提供 create/status/cancel/download，先給內部 UI 使用。
5. **Notifications**：Webhook/Email 完成通知。
6. **External Web UI App**：最後接上 API，確保後端穩定再開放外部。

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | 單 DB + 單佇列 + 單 GPU worker 足夠 |
| 1k-100k users | 佇列與 worker 分離部署，下載/校對可擴展多 worker |
| 100k+ users | 多 GPU + 分區佇列 + 物件儲存 + 分層快取 |

### Scaling Priorities

1. **First bottleneck:** GPU 轉錄吞吐（先確保佇列與優先級可控）。
2. **Second bottleneck:** LLM 校對 API 成本/速率限制（需可重試與退避）。

## Anti-Patterns

### Anti-Pattern 1: API 直接同步呼叫 Whisper

**What people do:** 在 API request 中直接執行轉錄。
**Why it's wrong:** 造成 request timeout、GPU 競爭、無法排程優先級。
**Do this instead:** API 只建立任務並交給 queue + worker。

### Anti-Pattern 2: Worker 直接改寫既有 pipeline 腳本

**What people do:** 直接修改 auto_* 腳本以支援外部功能。
**Why it's wrong:** 破壞既有內部流程，難以回退。
**Do this instead:** 以 wrapper/adapter 方式接入現有腳本。

### Anti-Pattern 3: 無狀態紀錄的「最佳努力」佇列

**What people do:** 只靠記憶體佇列，失敗後無法恢復。
**Why it's wrong:** 任務狀態丟失，外部客戶體驗差。
**Do this instead:** 任務狀態寫入持久化 Task DB。

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| YouTube | yt-dlp + scheduler | 需記錄下載狀態與重試策略 |
| ffmpeg | Worker 內部呼叫 | 轉檔與切片一致化 |
| LLM 校對 API | Proofread worker | 需速率限制與重試 |
| Email/Webhook | Notification service | 需可重送（idempotent） |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API ↔ Scheduler | 事件/任務狀態 | API 不決定 pipeline 邏輯 |
| Scheduler ↔ Workers | Queue | 工作者僅執行單一職責 |
| Workers ↔ Storage | 檔案/Metadata | 所有輸出需持久化 |
| Internal UI ↔ API | REST | 保持既有監控流程 |

## Sources

- /home/budaedu/ai-whisper/.planning/PROJECT.md

---
*Architecture research for: FaYin speech processing platform*
*Researched: 2026-03-21*

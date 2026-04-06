# Research: Phase 07 — 測試基礎設施與 API/Pipeline 自動化

> **目的**：規劃前的完整脈絡掌握，讓執行者能做出有根據的決策，避免踩坑。

---

## 1. 現狀快照（What already exists）

### 1.1 現有測試目錄結構
```
tests/
├── conftest.py              # 全域 fixtures（db_engine, db_session, user_fixture...）
├── fixtures/
│   └── test_audio.wav       # 96KB, 16kHz mono WAV — 已可直接複用
├── test_external_api_auth.py  # ✅ 7 個 auth 測試，全部 PASSING
├── test_external_api_tasks.py # ❌ 3 個佔位測試，assert False
├── test_external_api_download.py # ❌ 1 個佔位測試，assert False
├── test_scheduler_gpu_lock.py # ✅ GPU 單次序列化邏輯，PASSING
├── test_scheduler_integration.py # ✅ 排程器 + fan-out 整合，PASSING
├── test_lifespan_e2e.py     # ✅ FastAPI lifespan + scheduler E2E，PASSING
└── ... （共 30+ 個測試檔案，160 個 PASSING，21 個 FAILING）
```

### 1.2 整體測試健康度（2026-03-27）
- **160 passed / 21 failed**（排除 4 個 collection error 的模組）
- **Collection errors（需迴避或修復）：**
  - `test_diarization.py` — `Pipeline.from_pretrained()` API 問題（pyannote 版本）
  - `test_download_filter.py` — import error
  - `test_phase_06_integration.py` — `from main import app`（找不到 `main.py`）
  - `test_task_history_api.py` — 同上
- **主要 FAILING：**
  - `test_external_api_tasks.py`、`test_external_api_download.py` — 佔位 stub
  - `test_notebooklm_*.py` — NotebookLM 相關功能（與 Phase 07 無關）

### 1.3 現有 `tests/conftest.py` 提供的 fixtures
```python
db_engine    # StaticPool in-memory SQLite — 完整 Schema（Task, StageTask, ApiKey, User, Identity）
db_session   # Session（無 rollback，commit 後生效）
user_fixture # 已啟用的 external user + email Identity
disabled_user
mock_api_success_response, mock_api_reasoning_response
sample_srt_content, sample_subtitles
```

**重要：** `db_engine` 已有 `StaticPool`，確保同一 connection 物件被重用，適合測試。

---

## 2. 核心架構摘要（What to test）

### 2.1 Auth 層（`api/auth.py` + `api/routers/auth.py`）
| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/auth/login` | POST | Email + Password → access_token + refresh_token |
| `/api/auth/token` | POST | API Key（Header: x-api-key）→ JWT |
| `/api/auth/refresh` | POST | refresh_token → 新 token pair（舊 token 作廢） |
| `/api/auth/revoke` | POST | 撤銷並清除所有 refresh tokens |
| `/api/auth/google/login` | GET/POST | Google OAuth |
| `/api/auth/google/callback` | GET | Google callback |

**JWT 機制：** `JWT_SECRET`（env 優先，fallback `config.json.jwt_secret`）、`HS256`、預設 24h 過期。
**重要：** 測試時需 `monkeypatch.setenv("JWT_SECRET", "test-secret")` 並 patch `api.auth.JWT_SECRET`。

### 2.2 Tasks CRUD（`api/routers/tasks.py`）
| 端點 | 方法 | 說明 |
|------|------|------|
| `POST /api/tasks/` | multipart 或 JSON | 建立任務（type: upload \| youtube）|
| `GET /api/tasks/history` | JWT | 取得當前 user 的歷史任務列表 |
| `GET /api/tasks/{task_id}` | JWT | 取得單一任務（external 限制自己的，internal 不限）|
| `POST /api/tasks/{task_id}/cancel` | JWT | 取消任務（RBAC 控制）|

**角色隔離規則：**
- `role=external`：只能看/取消自己的 task（`requester == user_id`）
- `role=internal`：可以看所有 task（`requester` 不做過濾）
- `cancel_task()`：403 Forbidden 若 role=external 取消他人的

**建立任務會同時：**
1. 建立 `Task` 記錄（`TaskStatus.PENDING`）
2. 建立初始 `StageTask`（`StageType.DOWNLOAD`）
3. `log_task_event(task.id, 'created', ...)`

### 2.3 Download（`api/routers/download.py`）
- 路徑：`GET /api/tasks/{task_id}/download?format=...`
- 支援 `token` query parameter（除 Bearer header 外）
- 只有 `TaskStatus.DONE` 才能下載
- RBAC 同 tasks（external 只能下載自己的）
- 搜尋策略：先找 `OUTPUT_BASE/{video_id}/`，再找 `OUTPUT_BASE/{task_id}/`
- 回傳 `application/zip`，內含符合副檔名的檔案
- format alias：`word→.docx`、`excel→.xlsx`

**測試重點：** 需用 `monkeypatch` patch `api.routers.download.OUTPUT_BASE` 指向 `tmp_path`。

### 2.4 Pipeline 與 GPU Lock
```
StageType: DOWNLOAD → TRANSCRIBE → PROOFREAD → POSTPROCESS
```

**GPU Lock 機制（`gpu_lock.py`）：**
- 使用 `fcntl.flock`（LOCK_EX | LOCK_NB）
- Lock file: `{project_root}/gpu_whisper.lock`
- `acquire_gpu_lock()` → 成功回傳 fd，失敗回傳 None（非阻塞）
- `is_gpu_busy()` → bool，供外部查詢

**Scheduler GPU 保護（`pipeline/queue/scheduler.py`）：**
- `GPU_STAGES = {StageType.TRANSCRIBE}` — 僅 TRANSCRIBE 需要 GPU Lock
- 非 GPU stages（DOWNLOAD）可以 `DL_MAX_CONCURRENT=2` 並行

**Claim 邏輯（`pipeline/queue/repository.py`）：**
- `claim_next_stage(stage_filter=StageType.TRANSCRIBE)` — 已有 DB 層級的單 GPU 序列化
- 若已有 TRANSCRIBE running，不再 claim 第二個

---

## 3. 現有 Fixture 與 Mocking 模式（Pattern Reuse）

### 3.1 已驗證有效的 Test Client 模式（來自 `test_external_api_auth.py`）
```python
@pytest.fixture
def client(db_engine, monkeypatch):
    # 1. 建表
    SQLModel.metadata.create_all(db_engine)
    # 2. 覆蓋 session factory
    def _get_session(): return Session(db_engine)
    # 3. patch 模組依賴
    monkeypatch.setattr("api.routers.auth.get_session", _get_session)
    monkeypatch.setattr("pipeline.queue.database.get_session", _get_session)
    monkeypatch.setattr("pipeline.queue.database.get_engine", lambda: db_engine)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setattr("api.auth.JWT_SECRET", "test-secret")
    # 4. 建立 FastAPI app（只 include 需要的 router）
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")
    with TestClient(app) as test_client:
        yield test_client
```

**注意：** 不要使用 `api_server.app`（含 lifespan scheduler），除非刻意測試 lifespan。

### 3.2 已驗證的 Lifespan E2E 模式（來自 `test_lifespan_e2e.py`）
```python
with patch("pipeline.queue.scheduler.TaskScheduler.build_default_executors",
           return_value=_mock_executors):
    from api_server import app
    with TestClient(app) as client:
        yield client
```

### 3.3 OAuth 依賴 Stub 模式（來自 `test_external_api_auth.py`）
```python
# authlib 和 google-auth 不在基礎測試環境，需要 stub
sys.modules.setdefault("authlib", authlib_module)
sys.modules.setdefault("google.oauth2.id_token", google_oauth_module.id_token)
```

---

## 4. 關鍵技術陷阱（Gotchas）

### 4.1 `get_session()` 不是 context manager
```python
# 生產程式碼裡的用法（任務 router 中）：
with get_session() as session:
    ...
```
但 `pipeline/queue/database.py` 的 `get_session()` 回傳的是 `Session`（非 context manager 包裝）。
**解決：** `Session` 本身支援 `with` 語法，可直接使用。測試覆蓋時需確保 patch 的函式也回傳可 `with` 的物件。

### 4.2 `_engine` 全域單例問題
`pipeline/queue/database.py` 維護 `_engine` 全域變數。若測試之間 engine 洩漏，可能導致跨測試污染。
**解決：** 測試後需呼叫 `pipeline.queue.database.reset_engine()`，或 patch `get_engine`。

### 4.3 `api_server.py` 的 lifespan 會啟動 TaskScheduler 與 PlaylistSyncWorker
直接 import `api_server.app` 就會觸發 lifespan，需要 patch：
- `pipeline.queue.scheduler.TaskScheduler.build_default_executors`
- `pipeline.queue.scheduler.acquire_gpu_lock`
- `pipeline.queue.scheduler.release_gpu_lock`
- `api_server.create_db_and_tables`（避免寫入實體 DB）

### 4.4 `tasks.py` router 依賴 `OUTPUT_BASE`
```python
BASE_DIR = Path(__file__).resolve().parents[2]  # ai-whisper/
OUTPUT_BASE = BASE_DIR / "output"
```
Upload 任務會把檔案寫入 `OUTPUT_BASE / str(task.id) / filename`。
**解決：** `monkeypatch` patch `api.routers.tasks.OUTPUT_BASE` 指向 `tmp_path`（測試隔離）。

### 4.5 Download 路由器的 token query parameter 支援
`GET /api/tasks/{id}/download?token=xxx` — 與其他 endpoint 的純 Bearer 認證不同。
測試 download 時，也需驗證 query token 路徑。

### 4.6 `log_task_event` 依賴 `database.persistence`
`api/routers/tasks.py` 呼叫 `from database.persistence import log_task_event`，
而 `database/persistence.py` 寫入 `database.db`（舊版 SQLite）。
**解決：** 在 tasks CRUD 測試中 patch `api.routers.tasks.log_task_event` 為 no-op。

### 4.7 `tests/v2/` 目錄命名衝突注意
現有 `tests/` 已有大量測試（`conftest.py` 含通用 fixtures）。
新建 `tests/v2/conftest.py` 時，pytest 會「繼承」父層 `tests/conftest.py` 的 fixtures，
所以 `v2/conftest.py` 可以只寫**覆蓋**或**新增**的 fixture，不需重複定義 `db_engine` / `db_session` / `user_fixture`。

---

## 5. Plan 07-01 規劃細節

### 5.1 `tests/v2/test_config.v2.json` 需要的欄位
```json
{
  "database_url": "sqlite:///:memory:",
  "enable_webhook": false,
  "enable_mail": false,
  "whisper_model": "tiny",
  "llm_provider": "mock",
  "jwt_secret": "test-secret-v2"
}
```

**注意：** 現有的 `api/auth.py` 不從 config.json 讀取 `database_url`，它使用的是 `pipeline.queue.database._engine`。
`jwt_secret` 也是優先從 env 讀（`JWT_SECRET`），fallback `config.json.jwt_secret`。
因此 `test_config.v2.json` 對現有程式碼的影響是「語義性記錄」，實際注入需靠 fixture 的 `monkeypatch`。

### 5.2 `tests/v2/conftest.py` 的設計策略
由於現有 `tests/conftest.py` 已有完整的 `db_engine` 和 `db_session`，`tests/v2/conftest.py` 應：
1. **不重複定義** `db_engine`/`db_session`（直接繼承）
2. **定義 `client` fixture**（含 tasks + download + auth router 的完整 app）
3. **定義 `auth_header` fixture**（使用 `create_access_token` 產生 Bearer token）
4. **定義 `internal_auth_header` fixture**（role=internal 的 token）
5. **patch 全域副作用**（OUTPUT_BASE, log_task_event, get_session）

### 5.3 `tests/fixtures/v2/sample.wav`
現有 `tests/fixtures/test_audio.wav`（96KB, 16kHz mono）已可直接使用。
**建議：** 複製或 symlink 為 `tests/fixtures/v2/sample.wav`，未來 Smoke test 使用。

---

## 6. Plan 07-02 規劃細節

### 6.1 Auth 測試（`tests/v2/test_auth.py`）
**現有 `test_external_api_auth.py` 已覆蓋：**
- login success/failure
- disabled user
- password strength validation
- refresh token rotation
- revoke all tokens
- Google OAuth callback

**v2 Auth 測試應新增（補足空缺）：**
- `test_api_key_exchange`：`POST /api/auth/token`（x-api-key header）
- `test_expired_token_returns_401`：使用已過期的 JWT 訪問受保護端點
- `test_internal_role_access`：internal role 的 token 能訪問所有資料
- `test_external_role_isolation`：external role 只能看自己的任務

**重用策略：** 直接在 `test_external_api_auth.py` 補測試案例，或在 `tests/v2/test_auth.py` import 並重組，避免重複 fixture 設定。

### 6.2 Tasks CRUD 測試（`tests/v2/test_tasks_crud.py`）
需要 patch 的依賴：
```python
monkeypatch.setattr("api.routers.tasks.log_task_event", lambda *args, **kwargs: None)
monkeypatch.setattr("api.routers.tasks.OUTPUT_BASE", tmp_path)
monkeypatch.setattr("api.routers.tasks.get_session", _get_session)
# create_initial_stages 不需 patch — 直接操作 in-memory DB
```

**測試案例設計：**
| 測試 | 描述 |
|------|------|
| `test_create_youtube_task` | JSON body，type=youtube，確認 201 + task_id |
| `test_create_upload_task` | multipart，type=upload，附 WAV 檔案 |
| `test_get_task_status` | external user 查自己的任務 |
| `test_get_task_status_forbidden` | external user 查別人的任務 → 404 |
| `test_internal_can_see_all_tasks` | internal role 不受 requester 過濾 |
| `test_cancel_task` | 取消自己的任務 → status=canceled |
| `test_cancel_other_task_forbidden` | external 取消他人任務 → 403 |
| `test_task_history_pagination` | page/size 參數 |

### 6.3 Download 測試（`tests/v2/test_download.py`）
**需要預備的 fixture：**
```python
@pytest.fixture
def done_task_with_files(db_session, tmp_path):
    task = Task(title="Test", video_id="v_test", status=TaskStatus.DONE, requester="user123")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    output_dir = tmp_path / str(task.id)
    output_dir.mkdir()
    (output_dir / "result.docx").write_bytes(b"word content")
    (output_dir / "result.xlsx").write_bytes(b"excel content")
    (output_dir / "result.txt").write_text("text content")
    return task, output_dir
```

**測試案例設計：**
| 測試 | 描述 |
|------|------|
| `test_download_all_formats` | 無 format 參數，zip 包含全部 3 個檔 |
| `test_download_word_alias` | `?format=word` → zip 只含 .docx |
| `test_download_excel_alias` | `?format=excel` → zip 只含 .xlsx |
| `test_download_token_param` | `?token=xxx` 替代 Bearer header |
| `test_download_pending_task_400` | status=PENDING 時 → 400 |
| `test_download_not_done_404` | 找不到輸出檔案 → 404 |
| `test_download_forbidden_external` | external user 下載他人任務 → 403 |
| `test_zip_content_structure` | 解壓 zip 確認 arcname 正確 |

---

## 7. Plan 07-03 規劃細節

### 7.1 Pipeline 狀態機測試（`tests/v2/test_pipeline.py`）
**核心：用 mock executor 驗證狀態轉換**

已有 `tests/test_scheduler_integration.py` 涵蓋基礎情境。
`v2/test_pipeline.py` 應聚焦在：

| 情境 | 驗證點 |
|------|--------|
| 成功執行 | `DOWNLOAD` → `DONE`，fan-out 建立 `TRANSCRIBE` stage |
| Stage 拋出例外 | stage status → `FAILED`，task status → `FAILED` |
| Retry 觸發 | `retry_count + 1`，`next_retry_at` 設定正確 |
| Mock transcribe | `run_whisper` 被 patch，不調用真實 GPU |

**mock 攔截點：**
```python
# transcribe.py 內部 import
with patch("pipeline.stages.transcribe.execute") as mock_transcribe:
    mock_transcribe.return_value = {"srt_path": "...", "txt_path": "..."}
    ...
```

### 7.2 GPU 並發測試（`tests/v2/test_gpu_concurrency.py`）
**現有 `test_scheduler_gpu_lock.py` 已驗證：**
- `claim_next_stage(StageType.TRANSCRIBE)` 在已有 RUNNING 時不再 claim
- 非 GPU stages 可並行

**v2 應新增（系統層面）：**
```python
def test_gpu_lock_mutual_exclusion():
    """兩個 process 同時 acquire_gpu_lock，只有一個成功。"""
    import multiprocessing
    results = multiprocessing.Manager().list()
    # 用 multiprocessing 啟動兩個 worker 同時競搶
    ...
```

**注意：** `fcntl.flock` 的 LOCK_NB 是進程層面的互斥，需用 `multiprocessing` 而非 `threading`。

**gpu_lock 測試用的 lock file 隔離：**
```python
@pytest.fixture
def temp_lock_file(tmp_path, monkeypatch):
    lock_path = str(tmp_path / "test_gpu.lock")
    monkeypatch.setattr("gpu_lock.LOCK_FILE", lock_path)
    yield lock_path
```

### 7.3 Smoke E2E 測試（`tests/v2/test_smoke_e2e.py`）
**策略：**
1. 使用 `test_lifespan_e2e.py` 的 mock executor 模式
2. 提交 YouTube 任務（無需真實網路）
3. 手動觸發 `_scheduler._process_next()` 推進各 stage
4. 驗證最終 Task status = DONE

**執行流程：**
```python
# 1. 建立任務
response = client.post("/api/tasks/", json={"type": "youtube", ...})
task_id = response.json()["task_id"]

# 2. Mock executor 設定回傳值
_mock_executors[StageType.DOWNLOAD].return_value = None  # 不需 output

# 3. 推進 pipeline（DOWNLOAD → TRANSCRIBE → PROOFREAD → POSTPROCESS）
for _ in range(4):
    _run_process_next()

# 4. 驗證最終狀態
with _test_get_session() as s:
    task = s.get(Task, task_id)
assert task.status == TaskStatus.DONE
```

---

## 8. 依賴套件確認

### 8.1 已安裝（可直接使用）
| 套件 | 版本 | 用途 |
|------|------|------|
| `pytest` | 9.0.2 | 主要執行器 |
| `anyio` | 4.12.1 | async 測試支援 |
| `fastapi` | 0.135.1 | TestClient |
| `sqlmodel` | 0.0.37 | in-memory DB |
| `httpx` | 0.28.1 | TestClient 底層 |

### 8.2 未安裝（Phase 07 範圍外）
| 套件 | 說明 |
|------|------|
| `pytest-playwright` | Phase 08（UI E2E）才需要 |
| `playwright` | 同上 |

**結論：Phase 07 後端/Pipeline 測試不需要安裝任何新套件。**

---

## 9. 風險與對策

| 風險 | 嚴重度 | 對策 |
|------|--------|------|
| **`_engine` 全域污染**：測試間 engine 殘留導致 state 洩漏 | 高 | 每個 fixture 使用 `StaticPool + db_engine.dispose()`；`teardown` 呼叫 `reset_engine()` |
| **`lifespan` scheduler 未清除**：非同步 task 在測試結束後繼續跑 | 高 | 只使用 mock executor，不使用真實 executor；`test_lifespan_e2e.py` 已有良好範例 |
| **`log_task_event` 寫入 `database.db`**：tasks router 會呼叫舊版 persistence | 中 | `monkeypatch.setattr("api.routers.tasks.log_task_event", lambda *a, **k: None)` |
| **`OUTPUT_BASE` 寫入生產目錄**：upload 任務會寫入 `ai-whisper/output/` | 中 | `monkeypatch.setattr("api.routers.tasks.OUTPUT_BASE", tmp_path)` |
| **GPU Lock file 殘留**：並發測試後 lock file 未清除 | 低 | 使用 `temp_lock_file` fixture patch `gpu_lock.LOCK_FILE` 指向 `tmp_path` |
| **`test_phase_06_integration.py` import 錯誤**：`from main import app` 找不到 `main.py` | 已存在 | Phase 07 不觸及此檔，但應在 `tests/v2/` 中不重蹈此模式，固定用 `api_server.app` |

---

## 10. 規劃建議摘要

### Plan 07-01（建立環境）
- **關鍵決策**：`tests/v2/conftest.py` 繼承父層 `db_engine`/`db_session`，只新增 `client`、`auth_header`、`internal_auth_header` fixture。
- **`test_config.v2.json`** 是語義記錄，實際注入靠 `monkeypatch`。
- **`sample.wav`** 直接複製現有 `tests/fixtures/test_audio.wav`。
- **隔離驗證測試**：`test_isolation.py` 確認 `db_session` 不產生 `.db` 檔。

### Plan 07-02（後端 API 測試）
- **Auth**：複用 `test_external_api_auth.py` 的 OAuth stub 模式，補 API Key 與 RBAC 測試。
- **Tasks CRUD**：三大 patch 目標 = `get_session` + `OUTPUT_BASE` + `log_task_event`。
- **Download**：用 `tmp_path` + `Task.status=DONE` 的 fixture 建立 mock 環境，以 `zipfile` 解壓驗證內容。

### Plan 07-03（Pipeline 整合）
- **Pipeline 狀態機**：以 mock executor 驗證 `PENDING→RUNNING→DONE` 轉換與 fan-out。
- **GPU Lock**：用 `multiprocessing`（非 threading）驗證 `fcntl.flock` 的跨進程互斥；需 patch `gpu_lock.LOCK_FILE`。
- **Smoke E2E**：沿用 `test_lifespan_e2e.py` 的 mock executor 模式，4 輪 `_process_next()` 推進整個 pipeline。
- **執行時間目標**：全套 < 30 秒（mock 模式下應 < 10 秒）。

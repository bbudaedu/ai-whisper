---
plan: "05"
title: "API Server 整合、任務提交入口與排程器啟動"
phase: 1
wave: 2
depends_on:
  - "02"
  - "03"
  - "04"
requirements:
  - QUEUE-01
  - QUEUE-02
  - QUEUE-03
  - QUEUE-04
  - QUEUE-05
must_haves:
  truths:
    - FastAPI app 使用 lifespan 啟動/停止 scheduler
    - DB tables 在 startup 時自動建立
    - /api/task 路由擴展為佇列式提交（寫入 SQLite + create_initial_stages）
    - 現有 API 路由不受影響（不破壞既有功能）
    - 整合測試驗證 lifespan → scheduler → claim → execute → fan-out 流程
  artifacts:
    - api_server.py (modified — lifespan, /api/task queue branch, /api/queue/status)
    - pipeline/queue/scheduler.py (modified — build_default_executors)
    - tests/test_scheduler_integration.py
    - tests/test_api_task_submission.py
  key_links:
    - "api_server.py (lifespan) -> pipeline/queue/database.py (create_db_and_tables)"
    - "api_server.py (lifespan) -> pipeline/queue/scheduler.py (TaskScheduler.start/stop)"
    - "api_server.py (/api/task queue) -> pipeline/queue/repository.py (TaskRepository.create_task)"
    - "api_server.py (/api/task queue) -> pipeline/queue/stage_runner.py (create_initial_stages)"
    - "pipeline/queue/scheduler.py (build_default_executors) -> pipeline/stages/* (execute)"
    - "pipeline/queue/scheduler.py (_execute_stage) -> pipeline/queue/stage_runner.py (enqueue_next_stage)"
files_modified:
  - api_server.py
  - pipeline/queue/scheduler.py
  - tests/test_scheduler_integration.py
  - tests/test_api_task_submission.py
autonomous: true
---

# Plan 05: API Server 整合、任務提交入口與排程器啟動

## Goal
將排程器透過 FastAPI lifespan 整合至 `api_server.py`，在 server 啟動時初始化 DB、啟動 polling scheduler，shutdown 時優雅停止。**擴展 `/api/task` 路由使其將任務寫入 SQLite 佇列**（而非僅 `subprocess.Popen`），同時連接 stage_runner 的 fan-out 機制到 scheduler 的 `_process_next`，使完整 pipeline 可端對端運行。

## Tasks

<task id="05-01">
<title>擴展 scheduler 整合 stage_runner fan-out 與 context 建構</title>
<read_first>
- pipeline/queue/scheduler.py (TaskScheduler._process_next / _execute_stage)
- pipeline/queue/stage_runner.py (enqueue_next_stage / build_context_for_stage)
- pipeline/queue/repository.py (TaskRepository / save_stage_output)
- pipeline/stages/download.py (execute 介面)
- pipeline/stages/transcribe.py (execute 介面)
- pipeline/stages/proofread.py (execute 介面)
- pipeline/stages/postprocess.py (execute 介面)
</read_first>
<action>
修改 `pipeline/queue/scheduler.py`：

1. 在 `_execute_stage` 的成功路徑中，呼叫 `enqueue_next_stage` 已在 Plan 03 實作。

2. 新增 `build_default_executors` 類別方法，整合 stage module 與 output_payload 儲存：

```python
@classmethod
def build_default_executors(cls) -> dict[StageType, StageExecutor]:
    """建立預設的 stage executors 字典。"""
    from pipeline.stages import download, transcribe, proofread, postprocess
    from pipeline.queue.stage_runner import build_context_for_stage
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.database import get_session

    def _make_executor(stage_module):
        """包裝 stage.execute 為 StageExecutor（只接收 StageTask）。

        流程：
        1. 從 DB 建構 context（含前一 stage 的 output_payload）
        2. 呼叫 stage_module.execute(stage_task, context)
        3. 將回傳的 output dict 存入 output_payload
        """
        def executor(stage_task: StageTask) -> None:
            with get_session() as session:
                context = build_context_for_stage(session, stage_task)
            output = stage_module.execute(stage_task, context)
            if output and isinstance(output, dict):
                with get_session() as session:
                    repo = TaskRepository(session)
                    repo.save_stage_output(stage_task.id, output)
        return executor

    return {
        StageType.DOWNLOAD: _make_executor(download),
        StageType.TRANSCRIBE: _make_executor(transcribe),
        StageType.PROOFREAD: _make_executor(proofread),
        StageType.POSTPROCESS: _make_executor(postprocess),
    }
```

重點：
- executor 內先呼叫 `build_context_for_stage` 取得 context（含前一 stage output）
- 執行完畢後呼叫 `save_stage_output` 儲存 stage 結果
- 使用 `get_session()` 取得新 session 避免跨執行緒問題
</action>
<files>
- pipeline/queue/scheduler.py (modify — add build_default_executors)
</files>
<verify>
<automated>python -c "from pipeline.queue.scheduler import TaskScheduler; print('build_default_executors' in dir(TaskScheduler))"</automated>
</verify>
<done>
- pipeline/queue/scheduler.py 包含 def build_default_executors(
- pipeline/queue/scheduler.py 包含 build_context_for_stage
- pipeline/queue/scheduler.py 包含 save_stage_output
- pipeline/queue/scheduler.py 包含 StageType.DOWNLOAD
- pipeline/queue/scheduler.py 包含 StageType.PROOFREAD
- pipeline/queue/scheduler.py 包含 StageType.POSTPROCESS
</done>
</task>

<task id="05-02">
<title>整合排程器到 api_server.py 的 lifespan 並擴展 /api/task 為佇列提交</title>
<read_first>
- api_server.py (現有 FastAPI app 結構，/api/task route，所有 import 與 middleware)
- pipeline/queue/database.py (get_engine / create_db_and_tables / get_session)
- pipeline/queue/scheduler.py (TaskScheduler)
- pipeline/queue/repository.py (TaskRepository / create_task)
- pipeline/queue/stage_runner.py (create_initial_stages)
- .planning/phases/01-task-queue-scheduling/01-RESEARCH.md §Pattern 3 (lifespan 模式)
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md §Integration Points (/api/task 路由)
</read_first>
<action>
修改 `api_server.py`，加入 lifespan 啟動 scheduler 並擴展 `/api/task`：

1. 在檔案頂部的 import 區域加入：
```python
from contextlib import asynccontextmanager
from pipeline.queue.database import create_db_and_tables, get_session
from pipeline.queue.scheduler import TaskScheduler
from pipeline.queue.repository import TaskRepository
from pipeline.queue.stage_runner import create_initial_stages
from pipeline.queue.models import TaskSource, StageType
```

2. 在 `app = FastAPI()` 之前加入 lifespan 定義：
```python
# --- Task Queue Scheduler ---
_scheduler: TaskScheduler | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: 啟動排程器 + DB 初始化。"""
    global _scheduler

    # Startup: 初始化 DB 並啟動排程器
    create_db_and_tables()

    _scheduler = TaskScheduler(
        session_factory=get_session,
        stage_executors=TaskScheduler.build_default_executors(),
        poll_interval=5,
    )
    await _scheduler.start()

    yield

    # Shutdown: 停止排程器
    if _scheduler is not None:
        await _scheduler.stop()
        _scheduler = None
```

3. 修改 `app = FastAPI()` 為：
```python
app = FastAPI(lifespan=lifespan)
```

4. **擴展現有 `/api/task` 路由**，新增 `action="queue"` 選項將任務寫入 SQLite 佇列：

在現有 `manage_task` 函式的 `if/elif` 鏈中，新增一個分支：

```python
@app.post("/api/task")
def manage_task(req: TaskRequest):
    if req.action == "queue":
        # 新增：佇列式任務提交 → 寫入 SQLite
        if not req.target:
            return {"error": "Target (video_id) required"}
        title = getattr(req, "title", req.target)  # 容許 title 欄位
        source_str = getattr(req, "source", "external")
        source = TaskSource.INTERNAL if source_str == "internal" else TaskSource.EXTERNAL
        with get_session() as session:
            repo = TaskRepository(session)
            task = repo.create_task(
                title=title,
                video_id=req.target,
                source=source,
            )
            stage = create_initial_stages(session, task)
        return {
            "status": "queued",
            "task_id": task.id,
            "stage_id": stage.id,
            "video_id": req.target,
        }
    elif req.action == "proofread":
        # ... 保留現有邏輯 ...
    elif req.action == "whisper":
        # ... 保留現有邏輯 ...
```

5. 保留所有現有 middleware、路由、endpoint 不做任何修改。

6. 在現有的 `/api/task/status` endpoint 附近，新增佇列狀態 endpoint：
```python
@app.get("/api/queue/status")
def get_queue_status():
    """查詢任務佇列與排程器狀態。"""
    from pipeline.queue.database import get_session
    from pipeline.queue.repository import TaskRepository

    with get_session() as session:
        repo = TaskRepository(session)
        pending = repo.count_pending_stages()
        running = repo.get_running_stages()

    return {
        "scheduler_running": _scheduler is not None and _scheduler._running,
        "pending_stages": pending,
        "running_stages": len(running),
        "gpu_busy": is_gpu_busy(),
    }
```

注意事項：
- `/api/task` 的 `action="queue"` 是新增分支，不修改 `proofread`/`whisper` 等既有分支
- `lifespan` 搭配 `asynccontextmanager` 使用，符合 FastAPI 官方模式
- 現有所有路由不變動，確保不破壞既有功能
</action>
<files>
- api_server.py (modify — add lifespan, extend /api/task, add /api/queue/status)
</files>
<verify>
<automated>python -c "
import ast, sys
with open('api_server.py') as f:
    tree = ast.parse(f.read())
names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
checks = ['lifespan', 'get_queue_status', 'manage_task']
for c in checks:
    assert c in names, f'{c} not found in api_server.py'
print('OK: lifespan + get_queue_status + manage_task found')
"</automated>
</verify>
<done>
- api_server.py 包含 from contextlib import asynccontextmanager
- api_server.py 包含 from pipeline.queue.database import create_db_and_tables, get_session
- api_server.py 包含 from pipeline.queue.scheduler import TaskScheduler
- api_server.py 包含 async def lifespan(app: FastAPI):
- api_server.py 包含 app = FastAPI(lifespan=lifespan)
- api_server.py 包含 create_db_and_tables()
- api_server.py 包含 await _scheduler.start()
- api_server.py 包含 await _scheduler.stop()
- api_server.py 包含 action == "queue"
- api_server.py 包含 repo.create_task(
- api_server.py 包含 create_initial_stages(session, task)
- api_server.py 包含 @app.get("/api/queue/status")
- api_server.py 仍包含 @app.get("/api/config") (現有路由未被破壞)
- api_server.py 仍包含 @app.post("/api/task") (現有路由未被破壞)
- api_server.py 仍包含 @app.get("/api/dashboard") (現有路由未被破壞)
</done>
</task>

<task id="05-03">
<title>建立整合測試與任務提交測試</title>
<read_first>
- pipeline/queue/scheduler.py (TaskScheduler)
- pipeline/queue/repository.py (TaskRepository)
- pipeline/queue/stage_runner.py (enqueue_next_stage / create_initial_stages)
- pipeline/queue/models.py (所有模型)
- pipeline/queue/database.py (引擎設定)
- tests/conftest.py (db_engine / db_session fixture)
- api_server.py (lifespan / get_queue_status / manage_task queue branch)
</read_first>
<action>
建立 `tests/test_api_task_submission.py`：

```python
"""測試 /api/task action=queue 的任務提交入口。"""
import pytest
from pipeline.queue.repository import TaskRepository
from pipeline.queue.models import TaskStatus, TaskSource, StageType
from pipeline.queue.stage_runner import create_initial_stages


def test_queue_submission_creates_task_and_stage(db_session):
    """模擬 /api/task action=queue 的核心邏輯：建立 task + initial stage。"""
    repo = TaskRepository(db_session)

    # 模擬 API handler 的行為
    video_id = "submit_vid_001"
    title = "提交測試影片"
    source = TaskSource.EXTERNAL

    task = repo.create_task(
        title=title,
        video_id=video_id,
        source=source,
    )
    stage = create_initial_stages(db_session, task)

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.source == TaskSource.EXTERNAL
    assert task.priority == 0  # external = 0

    assert stage.stage == StageType.DOWNLOAD
    assert stage.status == TaskStatus.PENDING
    assert stage.task_id == task.id


def test_queue_submission_internal_priority(db_session):
    """內部任務提交時 priority=10。"""
    repo = TaskRepository(db_session)

    task = repo.create_task(
        title="Internal video",
        video_id="int_vid_001",
        source=TaskSource.INTERNAL,
    )
    stage = create_initial_stages(db_session, task)

    assert task.priority == 10
    assert stage.priority >= 10


def test_queue_submission_returns_ids(db_session):
    """提交後回傳 task_id 和 stage_id。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(title="ID test", video_id="id_vid")
    stage = create_initial_stages(db_session, task)

    # 模擬 API response
    response = {
        "status": "queued",
        "task_id": task.id,
        "stage_id": stage.id,
        "video_id": "id_vid",
    }
    assert response["task_id"] is not None
    assert response["stage_id"] is not None
    assert response["status"] == "queued"


def test_playlist_submission_creates_parent_and_children(db_session):
    """播放清單提交：建立父任務 + 每集子任務 + initial stages。"""
    repo = TaskRepository(db_session)

    parent = repo.create_playlist_parent_task(
        playlist_id="PL_submit",
        playlist_title="測試播放清單",
        source=TaskSource.INTERNAL,
    )

    videos = [
        {"id": "v001", "title": "EP 001"},
        {"id": "v002", "title": "EP 002"},
        {"id": "v003", "title": "EP 003"},
    ]

    for v in videos:
        child = repo.create_child_task(
            parent_task_id=parent.id,
            title=v["title"],
            video_id=v["id"],
            playlist_id="PL_submit",
            source=TaskSource.INTERNAL,
        )
        create_initial_stages(db_session, child)

    children = repo.get_child_tasks(parent.id)
    assert len(children) == 3
    for child in children:
        assert child.parent_task_id == parent.id
        stages = repo.get_stages_for_task(child.id)
        assert len(stages) == 1
        assert stages[0].stage == StageType.DOWNLOAD
```

注意事項：
- `test_api_task_submission.py` 測試的是任務提交的核心邏輯（不需 HTTP client）
- `test_scheduler_integration.py` 已在 Plan 03 建立
</action>
<files>
- tests/test_api_task_submission.py (new)
</files>
<verify>
<automated>pytest -q tests/test_api_task_submission.py -x</automated>
</verify>
<done>
- tests/test_api_task_submission.py 包含 def test_queue_submission_creates_task_and_stage(
- tests/test_api_task_submission.py 包含 def test_playlist_submission_creates_parent_and_children(
- 執行 pytest -q 結果全部 passed
</done>
</task>

<task id="05-04">
<title>執行完整測試套件並驗證既有測試不受影響</title>
<read_first>
- tests/ (所有現有測試檔案)
- api_server.py (修改後版本)
- pipeline/queue/ (所有新建模組)
- pipeline/stages/ (所有新建模組)
</read_first>
<action>
1. 執行完整測試套件：
```bash
pytest -q
```

2. 確認所有新增測試通過：
```bash
pytest -q tests/test_task_queue.py tests/test_scheduler_gpu_lock.py tests/test_scheduler_priority.py tests/test_pipeline_stages.py tests/test_retry_policy.py tests/test_scheduler_integration.py tests/test_migration_fallback.py tests/test_api_task_submission.py
```

3. 確認所有既有測試不受影響（重點檢查）：
```bash
pytest -q tests/test_gpu_lock.py tests/test_playlist_manager.py tests/test_pipeline.py
```

4. 若有測試失敗，分析原因並修復（不修改測試本身的斷言邏輯，只修正新代碼中的問題）。

5. 確認 `api_server.py` 的所有既有 endpoint 仍存在：
- 手動 grep 確認：`/api/config`, `/api/status`, `/api/task`, `/api/dashboard`, `/api/playlists`, `/api/notebooklm/status`
</action>
<files>
- (no new files — validation only)
</files>
<verify>
<automated>pytest -q</automated>
</verify>
<done>
- 執行 pytest -q 結果無 error 且無 fail（skip 可接受）
- api_server.py 包含 @app.get("/api/config")
- api_server.py 包含 @app.post("/api/task")
- api_server.py 包含 @app.get("/api/dashboard")
- api_server.py 包含 @app.get("/api/playlists")
- api_server.py 包含 @app.get("/api/queue/status")
- api_server.py 包含 app = FastAPI(lifespan=lifespan)
</done>
</task>

## Verification

```bash
# 完整套件
pytest -q

# 新增模組結構
ls pipeline/queue/models.py pipeline/queue/database.py pipeline/queue/repository.py pipeline/queue/scheduler.py pipeline/queue/stage_runner.py pipeline/queue/backoff.py pipeline/queue/migration.py
ls pipeline/stages/download.py pipeline/stages/transcribe.py pipeline/stages/proofread.py pipeline/stages/postprocess.py

# API server 整合
grep "lifespan" api_server.py
grep "create_db_and_tables" api_server.py
grep "/api/queue/status" api_server.py
grep 'action == "queue"' api_server.py

# 任務提交入口
grep "create_initial_stages" api_server.py
grep "repo.create_task" api_server.py

# 既有路由保留
grep "/api/config" api_server.py
grep "/api/dashboard" api_server.py
```

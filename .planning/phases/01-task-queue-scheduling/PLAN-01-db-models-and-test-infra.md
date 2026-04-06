---
plan: "01"
title: "SQLite 資料模型與測試基礎設施"
phase: 1
wave: 0
depends_on: []
requirements:
  - QUEUE-01
  - QUEUE-02
  - QUEUE-03
  - QUEUE-04
  - QUEUE-05
must_haves:
  truths:
    - 任務可被持久化至 SQLite 並可靠讀回
    - Stage 間可透過 output_payload 欄位傳遞資料
    - 退避排程透過 next_retry_at 欄位控制 claim 時機
    - 測試基礎設施提供可重複使用的 in-memory DB fixture
  artifacts:
    - pipeline/queue/__init__.py
    - pipeline/queue/models.py
    - pipeline/queue/database.py
    - tests/conftest.py (db_engine / db_session fixtures)
    - tests/test_task_queue.py
    - tests/test_scheduler_gpu_lock.py
    - tests/test_scheduler_priority.py
    - tests/test_pipeline_stages.py
    - tests/test_retry_policy.py
  key_links:
    - "pipeline/queue/models.py (Task, StageTask) -> pipeline/queue/database.py (create_db_and_tables)"
    - "tests/conftest.py (db_engine, db_session) -> pipeline/queue/models.py"
files_modified:
  - pipeline/queue/__init__.py
  - pipeline/queue/models.py
  - pipeline/queue/database.py
  - tests/conftest.py
  - tests/test_task_queue.py
  - tests/test_scheduler_gpu_lock.py
  - tests/test_scheduler_priority.py
  - tests/test_pipeline_stages.py
  - tests/test_retry_policy.py
autonomous: true
---

# Plan 01: SQLite 資料模型與測試基礎設施

## Goal
建立 SQLite + SQLModel 任務資料模型（Task、StageTask）與 DB 引擎設定，以及所有 Phase 1 所需的測試 stub 與 fixture，為後續 Plan 02-05 提供可靠基礎。

## Tasks

<task id="01-01">
<title>建立 pipeline/queue 套件與 SQLModel 資料模型</title>
<read_first>
- pipeline/__init__.py (確認現有套件結構)
- pipeline/notebooklm_scheduler.py (參考現有 QueueItem/TaskStatus 設計模式)
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md (鎖定的決策)
- .planning/phases/01-task-queue-scheduling/01-RESEARCH.md (推薦的 schema 與模式)
</read_first>
<action>
1. 建立目錄 `pipeline/queue/`

2. 建立 `pipeline/queue/__init__.py`，內容：
```python
"""Task queue and scheduling package."""
```

3. 建立 `pipeline/queue/models.py`，定義以下 SQLModel 模型：

```python
import enum
import json
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class TaskSource(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class StageType(str, enum.Enum):
    DOWNLOAD = "download"
    TRANSCRIBE = "transcribe"
    PROOFREAD = "proofread"
    POSTPROCESS = "postprocess"

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    video_id: str = Field(index=True)
    playlist_id: str = Field(default="")
    source: TaskSource = Field(default=TaskSource.INTERNAL)
    status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    priority: int = Field(default=0)  # higher = more urgent
    max_retries: int = Field(default=3)
    retry_count: int = Field(default=0)
    error_message: str = Field(default="")
    parent_task_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

class StageTask(SQLModel, table=True):
    __tablename__ = "stage_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True, foreign_key="tasks.id")
    stage: StageType
    status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    priority: int = Field(default=0)
    source: TaskSource = Field(default=TaskSource.INTERNAL)
    max_retries: int = Field(default=3)
    retry_count: int = Field(default=0)
    error_message: str = Field(default="")
    output_payload: str = Field(default="")  # JSON string: stage 輸出供下一 stage 使用
    next_retry_at: Optional[datetime] = Field(default=None, index=True)  # 退避排程時間
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    def get_output(self) -> dict:
        """取得 output_payload 解析後的 dict。"""
        if not self.output_payload:
            return {}
        return json.loads(self.output_payload)

    def set_output(self, data: dict) -> None:
        """設定 output_payload（序列化為 JSON）。"""
        self.output_payload = json.dumps(data, ensure_ascii=False)
```

- `Task` 表示父任務（播放清單或單一影片任務）
- `StageTask` 表示每個 stage 的獨立子任務
- `source` 欄位用於區分 internal / external，供排程器優先權查詢
- `priority` 欄位預設 0，internal 任務可設定為 10（CONTEXT.md 決策：內部佇列先清空）
- `output_payload` JSON 欄位儲存 stage 的執行結果（如 audio_path, srt_path），供下一 stage 讀取
- `next_retry_at` 搭配指數退避，排程器只 claim 已到時間的任務
- 在 `status` 和 `task_id` 上建立索引
</action>
<files>
- pipeline/queue/__init__.py (new)
- pipeline/queue/models.py (new)
</files>
<verify>
<automated>pytest -q tests/test_task_queue.py::test_create_task_smoke tests/test_task_queue.py::test_create_stage_task_smoke -x</automated>
</verify>
<done>
- pipeline/queue/__init__.py 檔案存在
- pipeline/queue/models.py 包含 class Task(SQLModel, table=True):
- pipeline/queue/models.py 包含 class StageTask(SQLModel, table=True):
- pipeline/queue/models.py 包含 class TaskSource(str, enum.Enum):
- pipeline/queue/models.py 包含 class TaskStatus(str, enum.Enum):
- pipeline/queue/models.py 包含 class StageType(str, enum.Enum):
- Task 模型包含欄位：id, title, video_id, playlist_id, source, status, priority, max_retries, retry_count, error_message, parent_task_id, created_at, updated_at, completed_at
- StageTask 模型包含欄位：id, task_id, stage, status, priority, source, max_retries, retry_count, error_message, output_payload, next_retry_at, created_at, updated_at, started_at, completed_at
- StageTask 包含 get_output / set_output 方法
- pipeline/queue/models.py 包含 PENDING = "pending"
- pipeline/queue/models.py 包含 RUNNING = "running"
- pipeline/queue/models.py 包含 DONE = "done"
- pipeline/queue/models.py 包含 FAILED = "failed"
- pipeline/queue/models.py 包含 DOWNLOAD = "download"
- pipeline/queue/models.py 包含 TRANSCRIBE = "transcribe"
- pipeline/queue/models.py 包含 PROOFREAD = "proofread"
- pipeline/queue/models.py 包含 POSTPROCESS = "postprocess"
</done>
</task>

<task id="01-02">
<title>建立 SQLite 引擎設定模組 (database.py)</title>
<read_first>
- pipeline/queue/models.py (剛建立的模型)
- .planning/phases/01-task-queue-scheduling/01-RESEARCH.md (SQLite WAL / check_same_thread / busy_timeout 設定)
</read_first>
<action>
建立 `pipeline/queue/database.py`，提供 engine 建立與 Session 取得函式：

```python
import os
from sqlmodel import SQLModel, Session, create_engine

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "task_queue.db",
)

_engine = None

def get_engine(db_path: str | None = None):
    """取得或建立 SQLite engine（單例模式）。

    設定：
    - WAL 模式（提高並發讀取效能）
    - busy_timeout = 5000ms（避免 SQLITE_BUSY）
    - check_same_thread = False（允許多執行緒存取）
    """
    global _engine
    if _engine is not None:
        return _engine

    if db_path is None:
        db_path = _DEFAULT_DB_PATH

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db_url = f"sqlite:///{db_path}"

    _engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # 啟用 WAL 模式與 busy_timeout
    with _engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        conn.exec_driver_sql("PRAGMA busy_timeout=5000")
        conn.commit()

    return _engine


def create_db_and_tables(engine=None):
    """建立所有 SQLModel 資料表。"""
    if engine is None:
        engine = get_engine()
    # 確保 models 已被載入
    from pipeline.queue.models import Task, StageTask  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session(engine=None) -> Session:
    """建立新的 Session。"""
    if engine is None:
        engine = get_engine()
    return Session(engine)


def reset_engine():
    """重設 engine（用於測試）。"""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
```

注意事項：
- DB 預設存放在 `data/task_queue.db`（專案根目錄下的 `data/` 子目錄），避免放在 NAS
- WAL 模式透過 `PRAGMA journal_mode=WAL` 設定
- busy_timeout 設定 5000ms，降低 SQLITE_BUSY 機率
- `check_same_thread=False` 允許 FastAPI 背景任務與 API handler 跨執行緒存取
- `reset_engine()` 供測試使用，確保每個測試可以重建乾淨的 engine
</action>
<files>
- pipeline/queue/database.py (new)
</files>
<verify>
<automated>python -c "from pipeline.queue.database import get_engine, create_db_and_tables, get_session, reset_engine; print('OK')"</automated>
</verify>
<done>
- pipeline/queue/database.py 包含 def get_engine(
- pipeline/queue/database.py 包含 def create_db_and_tables(
- pipeline/queue/database.py 包含 def get_session(
- pipeline/queue/database.py 包含 def reset_engine(
- pipeline/queue/database.py 包含 "check_same_thread": False
- pipeline/queue/database.py 包含 PRAGMA journal_mode=WAL
- pipeline/queue/database.py 包含 PRAGMA busy_timeout=5000
- pipeline/queue/database.py 包含 task_queue.db
</done>
</task>

<task id="01-03">
<title>建立測試 fixture 與所有 QUEUE requirement 的 test stub</title>
<read_first>
- tests/conftest.py (現有 fixture，需擴展而非覆蓋)
- pipeline/queue/models.py (剛建立的模型)
- pipeline/queue/database.py (剛建立的引擎設定)
- .planning/phases/01-task-queue-scheduling/01-VALIDATION.md (測試檔案清單與驗證指令)
</read_first>
<action>
1. 擴展 `tests/conftest.py`，在現有 fixture 之後新增 SQLite 測試 fixture：

```python
# --- Task Queue Test Fixtures ---
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

@pytest.fixture
def db_engine():
    """建立 in-memory SQLite engine（每個測試獨立）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from pipeline.queue.models import Task, StageTask  # noqa: F401
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    """建立 Session，測試後自動 rollback。"""
    with Session(db_engine) as session:
        yield session
```

2. 建立以下 test stub 檔案（每個檔案至少包含一個可執行的 placeholder 測試）：

`tests/test_task_queue.py`:
```python
"""QUEUE-01: 系統提供異步任務佇列，任務提交後排隊等待 GPU 資源。"""
import pytest

def test_enqueue_pending(db_session):
    """任務提交後狀態為 pending。"""
    pytest.skip("Stub -- will be implemented in Plan 02")

def test_task_persisted_in_sqlite(db_session):
    """任務寫入 SQLite 後可被讀取。"""
    pytest.skip("Stub -- will be implemented in Plan 02")
```

`tests/test_scheduler_gpu_lock.py`:
```python
"""QUEUE-02: 單 GPU 排程機制，一次只執行一個 Whisper 任務。"""
import pytest

def test_single_gpu_enforced(db_session):
    """確保同時只有一個 running 的 transcribe stage。"""
    pytest.skip("Stub -- will be implemented in Plan 03")
```

`tests/test_scheduler_priority.py`:
```python
"""QUEUE-03: 內部任務優先於外部任務執行。"""
import pytest

def test_internal_before_external(db_session):
    """排程器優先 claim internal 任務。"""
    pytest.skip("Stub -- will be implemented in Plan 02")
```

`tests/test_pipeline_stages.py`:
```python
"""QUEUE-04: 工作流模組化為獨立 stage，各 stage 可並行。"""
import pytest

def test_stage_fanout(db_session):
    """stage 完成後自動 enqueue 下一 stage。"""
    pytest.skip("Stub -- will be implemented in Plan 04")
```

`tests/test_retry_policy.py`:
```python
"""QUEUE-05: 失敗任務自動重試（可設定重試次數）。"""
import pytest

def test_retry_backoff(db_session):
    """失敗 stage 會根據 retry_count 計算退避延遲。"""
    pytest.skip("Stub -- will be implemented in Plan 02")

def test_retry_count_incremented(db_session):
    """重試後 retry_count 加 1。"""
    pytest.skip("Stub -- will be implemented in Plan 02")

def test_max_retries_exceeded(db_session):
    """超過 max_retries 後狀態變為 failed。"""
    pytest.skip("Stub -- will be implemented in Plan 02")
```

3. 確認 `pytest -q` 可以執行所有 stub 測試（全部 skip，0 fail）。
</action>
<files>
- tests/conftest.py (modify — append fixtures)
- tests/test_task_queue.py (new)
- tests/test_scheduler_gpu_lock.py (new)
- tests/test_scheduler_priority.py (new)
- tests/test_pipeline_stages.py (new)
- tests/test_retry_policy.py (new)
</files>
<verify>
<automated>pytest -q tests/test_task_queue.py tests/test_scheduler_gpu_lock.py tests/test_scheduler_priority.py tests/test_pipeline_stages.py tests/test_retry_policy.py</automated>
</verify>
<done>
- tests/conftest.py 包含 def db_engine(
- tests/conftest.py 包含 def db_session(
- tests/conftest.py 包含 poolclass=StaticPool
- tests/conftest.py 包含 "sqlite://"
- 所有 5 個 test stub 檔案存在
- 執行 pytest -q 結果無 error（所有 stub 為 skip 或 pass）
</done>
</task>

<task id="01-04">
<title>驗證模型可建表並寫入讀取（DB 煙霧測試）</title>
<read_first>
- pipeline/queue/models.py
- pipeline/queue/database.py
- tests/conftest.py (db_engine / db_session fixture)
</read_first>
<action>
在 `tests/test_task_queue.py` 增加非 skip 的煙霧測試，驗證模型和 DB 設定可以正常運作：

```python
from pipeline.queue.models import Task, StageTask, TaskStatus, TaskSource, StageType

def test_create_task_smoke(db_session):
    """煙霧測試：可以建立 Task 並從 DB 讀回。"""
    task = Task(
        title="測試影片",
        video_id="abc123",
        playlist_id="pl_001",
        source=TaskSource.INTERNAL,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.source == TaskSource.INTERNAL
    assert task.video_id == "abc123"

def test_create_stage_task_smoke(db_session):
    """煙霧測試：可以建立 StageTask 並關聯到 Task。"""
    task = Task(title="測試", video_id="xyz789")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    stage = StageTask(
        task_id=task.id,
        stage=StageType.DOWNLOAD,
        status=TaskStatus.PENDING,
        source=task.source,
        priority=task.priority,
    )
    db_session.add(stage)
    db_session.commit()
    db_session.refresh(stage)

    assert stage.id is not None
    assert stage.task_id == task.id
    assert stage.stage == StageType.DOWNLOAD

def test_stage_task_output_payload(db_session):
    """煙霧測試：output_payload 可儲存與讀取 stage 輸出資料。"""
    task = Task(title="Payload test", video_id="pl_test")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    stage = StageTask(task_id=task.id, stage=StageType.DOWNLOAD)
    stage.set_output({"audio_path": "/tmp/test.m4a", "episode_dir": "/tmp/ep001"})
    db_session.add(stage)
    db_session.commit()
    db_session.refresh(stage)

    output = stage.get_output()
    assert output["audio_path"] == "/tmp/test.m4a"
    assert output["episode_dir"] == "/tmp/ep001"

def test_stage_task_next_retry_at(db_session):
    """煙霧測試：next_retry_at 欄位可設定與讀取。"""
    from datetime import datetime, timedelta
    task = Task(title="Retry at test", video_id="retry_at")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    future = datetime.utcnow() + timedelta(seconds=30)
    stage = StageTask(task_id=task.id, stage=StageType.TRANSCRIBE, next_retry_at=future)
    db_session.add(stage)
    db_session.commit()
    db_session.refresh(stage)

    assert stage.next_retry_at is not None
    assert stage.next_retry_at >= datetime.utcnow()
```

確保執行 `pytest -q tests/test_task_queue.py` 時煙霧測試通過，stub 測試顯示 skip。
</action>
<files>
- tests/test_task_queue.py (modify — add smoke tests)
</files>
<verify>
<automated>pytest -q tests/test_task_queue.py -x</automated>
</verify>
<done>
- tests/test_task_queue.py 包含 def test_create_task_smoke(
- tests/test_task_queue.py 包含 def test_create_stage_task_smoke(
- tests/test_task_queue.py 包含 def test_stage_task_output_payload(
- tests/test_task_queue.py 包含 def test_stage_task_next_retry_at(
- 執行 pytest -q tests/test_task_queue.py 結果包含 4 passed 且無 error
</done>
</task>

## Verification

```bash
# 結構驗證
ls pipeline/queue/__init__.py pipeline/queue/models.py pipeline/queue/database.py

# 模型驗證
grep -c "class Task" pipeline/queue/models.py    # 應為 1
grep -c "class StageTask" pipeline/queue/models.py  # 應為 1
grep "output_payload" pipeline/queue/models.py     # 確認 stage 輸出欄位
grep "next_retry_at" pipeline/queue/models.py       # 確認退避排程欄位

# 測試執行
pytest -q tests/test_task_queue.py tests/test_scheduler_gpu_lock.py tests/test_scheduler_priority.py tests/test_pipeline_stages.py tests/test_retry_policy.py
```

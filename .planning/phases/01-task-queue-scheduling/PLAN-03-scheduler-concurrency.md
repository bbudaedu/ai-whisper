---
plan: "03"
title: "排程器與下載併行控制"
phase: 1
wave: 1
depends_on:
  - "01"
requirements:
  - QUEUE-01
  - QUEUE-02
  - QUEUE-03
  - QUEUE-05
must_haves:
  truths:
    - 排程器一次只允許一個 transcribe stage running（QUEUE-02）
    - 排程器支援 download 2 併行（dl_semaphore）
    - GPU 忙碌時 transcribe stage 退回 pending 不計入 retry_count
    - 所有 stub 測試替換為真正的測試邏輯並通過
  artifacts:
    - pipeline/queue/scheduler.py
    - tests/test_scheduler_gpu_lock.py (stubs replaced with real tests)
    - tests/test_scheduler_integration.py
  key_links:
    - "pipeline/queue/scheduler.py (TaskScheduler) -> pipeline/queue/repository.py (TaskRepository.claim_next_stage)"
    - "pipeline/queue/scheduler.py (_execute_gpu_stage) -> gpu_lock.py (acquire_gpu_lock, release_gpu_lock)"
    - "pipeline/queue/scheduler.py (_execute_stage) -> pipeline/queue/stage_runner.py (enqueue_next_stage)"
    - "pipeline/queue/scheduler.py (_execute_stage) -> pipeline/queue/backoff.py (calculate_backoff, should_retry)"
files_modified:
  - pipeline/queue/scheduler.py
  - tests/test_scheduler_gpu_lock.py
  - tests/test_scheduler_integration.py
autonomous: true
---

# Plan 03: 排程器與下載併行控制

## Goal
實作排程器 polling loop（整合 gpu_lock.py + download 2 併行），涵蓋 QUEUE-01、02、03、05 的排程面向核心邏輯。排程器以 asyncio task 方式運行，支援 GPU 鎖定、下載併行限制、以及失敗重試整合。

## Tasks

<task id="03-01">
<title>實作排程器 (scheduler.py) 含 download 併行</title>
<read_first>
- pipeline/queue/repository.py (TaskRepository API)
- pipeline/queue/backoff.py (calculate_backoff / should_retry)
- pipeline/queue/models.py (TaskStatus / StageType)
- gpu_lock.py (acquire_gpu_lock / release_gpu_lock / is_gpu_busy)
- auto_youtube_whisper.py (dl_semaphore 用法，Semaphore(3))
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md §排程與優先權機制、§Pipeline Stage 並行策略
- .planning/phases/01-task-queue-scheduling/01-RESEARCH.md §Pattern 3 (lifespan 啟動)
</read_first>
<action>
建立 `pipeline/queue/scheduler.py`：

```python
"""任務佇列排程器 — Polling loop + GPU lock + download 併行 + 優先權排程。"""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional

from sqlmodel import Session

from pipeline.queue.models import StageTask, StageType, TaskStatus
from pipeline.queue.repository import TaskRepository
from pipeline.queue.backoff import calculate_backoff, should_retry
from gpu_lock import acquire_gpu_lock, release_gpu_lock

logger = logging.getLogger(__name__)

# Stage 執行函式的型別：接收 StageTask，回傳 None（成功）或 raise Exception
StageExecutor = Callable[[StageTask], None]

# 需要 GPU 的 stage 類型
GPU_STAGES = {StageType.TRANSCRIBE}

# 下載最大併行數（沿用 auto_youtube_whisper.py 的 dl_semaphore 模式，限制為 2）
DL_MAX_CONCURRENT = 2

POLL_INTERVAL = 5  # 秒


class TaskScheduler:
    """Polling-based 排程器。

    - 每隔 POLL_INTERVAL 秒檢查佇列
    - 對 GPU stage（transcribe）取得 gpu_lock 後才執行
    - 對 download stage 限制最多 DL_MAX_CONCURRENT 個同時執行
    - 非 GPU/非 download stage（proofread, postprocess）直接執行
    - 內部任務透過 priority 排序自動優先
    """

    def __init__(
        self,
        session_factory: Callable[[], Session],
        stage_executors: Optional[dict[StageType, StageExecutor]] = None,
        poll_interval: int = POLL_INTERVAL,
        dl_max_concurrent: int = DL_MAX_CONCURRENT,
    ):
        self.session_factory = session_factory
        self.stage_executors = stage_executors or {}
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._dl_semaphore = asyncio.Semaphore(dl_max_concurrent)

    async def start(self) -> None:
        """啟動排程器（作為 asyncio task）。"""
        if self._running:
            logger.warning("排程器已在執行中")
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"排程器已啟動（polling 間隔: {self.poll_interval}s）")

    async def stop(self) -> None:
        """停止排程器。"""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("排程器已停止")

    async def _poll_loop(self) -> None:
        """主 polling loop。"""
        while self._running:
            try:
                await self._process_next()
            except Exception as e:
                logger.error(f"排程器 poll 發生錯誤: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def _process_next(self) -> None:
        """嘗試處理下一個可用的 stage task。"""
        session = self.session_factory()
        try:
            repo = TaskRepository(session)

            # 嘗試 claim 下一個 pending stage
            stage_task = repo.claim_next_stage()
            if stage_task is None:
                return  # 無待處理任務

            logger.info(
                f"已 claim stage task #{stage_task.id}: "
                f"stage={stage_task.stage}, task_id={stage_task.task_id}, "
                f"source={stage_task.source}"
            )

            # 根據 stage 類型決定執行方式
            if stage_task.stage in GPU_STAGES:
                await self._execute_gpu_stage(session, repo, stage_task)
            elif stage_task.stage == StageType.DOWNLOAD:
                await self._execute_download_stage(session, repo, stage_task)
            else:
                await self._execute_stage(session, repo, stage_task)

        finally:
            session.close()

    async def _execute_gpu_stage(
        self, session: Session, repo: TaskRepository, stage_task: StageTask
    ) -> None:
        """執行需要 GPU 的 stage（取得 gpu_lock 後才執行）。"""
        gpu_lock_fd = acquire_gpu_lock()
        if gpu_lock_fd is None:
            # GPU 忙碌，退回 pending 等下一輪（不計入 retry_count）
            logger.info(f"GPU 忙碌，stage #{stage_task.id} 退回 pending")
            stage = session.get(StageTask, stage_task.id)
            if stage:
                stage.status = TaskStatus.PENDING
                stage.started_at = None
                stage.updated_at = datetime.utcnow()
                session.commit()
            return

        try:
            await self._execute_stage(session, repo, stage_task)
        finally:
            release_gpu_lock(gpu_lock_fd)

    async def _execute_download_stage(
        self, session: Session, repo: TaskRepository, stage_task: StageTask
    ) -> None:
        """執行 download stage（受 dl_semaphore 限制併行數）。"""
        # 檢查 download 併行數
        running_downloads = repo.get_running_stages(stage_filter=StageType.DOWNLOAD)
        # 排除自己（剛被 claim 為 running）
        other_running = [s for s in running_downloads if s.id != stage_task.id]
        if len(other_running) >= DL_MAX_CONCURRENT:
            # 已達下載上限，退回 pending
            logger.info(
                f"下載併行已滿 ({DL_MAX_CONCURRENT})，"
                f"stage #{stage_task.id} 退回 pending"
            )
            stage = session.get(StageTask, stage_task.id)
            if stage:
                stage.status = TaskStatus.PENDING
                stage.started_at = None
                stage.updated_at = datetime.utcnow()
                session.commit()
            return

        async with self._dl_semaphore:
            await self._execute_stage(session, repo, stage_task)

    async def _execute_stage(
        self, session: Session, repo: TaskRepository, stage_task: StageTask
    ) -> None:
        """通用 stage 執行邏輯。"""
        try:
            # 取得對應的 stage executor
            executor = self.stage_executors.get(stage_task.stage)
            if executor is None:
                raise RuntimeError(
                    f"無 executor 註冊給 stage: {stage_task.stage}"
                )

            # 在 executor 中執行（可能是 blocking，用 to_thread）
            await asyncio.to_thread(executor, stage_task)

            # 成功 → 標記完成
            repo.complete_stage(stage_task.id)
            logger.info(f"Stage #{stage_task.id} ({stage_task.stage}) 完成")

            # Fan-out: 自動建立下一 stage
            from pipeline.queue.stage_runner import enqueue_next_stage
            session.refresh(stage_task)
            enqueue_next_stage(session, stage_task)

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Stage #{stage_task.id} ({stage_task.stage}) 執行失敗: {error_msg}"
            )

            # 嘗試重試（含指數退避）
            if should_retry(stage_task.retry_count, stage_task.max_retries):
                backoff_delay = calculate_backoff(stage_task.retry_count)
                retried = repo.mark_stage_for_retry(
                    stage_task.id, error_msg, backoff_seconds=backoff_delay
                )
                if retried:
                    logger.info(
                        f"Stage #{stage_task.id} 排入重試 "
                        f"(retry {stage_task.retry_count + 1}/{stage_task.max_retries}, "
                        f"退避 {backoff_delay:.1f}s, "
                        f"next_retry_at 已設定)"
                    )
                else:
                    logger.error(
                        f"Stage #{stage_task.id} 超過重試上限 "
                        f"({stage_task.max_retries} 次)，標記 failed"
                    )
            else:
                repo.fail_stage(stage_task.id, error_msg)
                logger.error(
                    f"Stage #{stage_task.id} 標記 failed: {error_msg}"
                )
```

設計重點：
- `session_factory` 注入，方便測試時替換為 test session
- `stage_executors` 字典注入，各 stage 的執行函式在 Plan 04 中實作
- GPU stage 才取 `gpu_lock`，非 GPU stage 直接執行
- **download stage 受 `_dl_semaphore` + running count 限制，最多 2 併行**
- `asyncio.to_thread` 包裝 blocking executor，不阻塞 event loop
- GPU busy 時退回 pending 不計入 retry_count
- 失敗時 `calculate_backoff` 計算退避秒數，傳入 `mark_stage_for_retry` 設定 `next_retry_at`
- `POLL_INTERVAL = 5` 秒（保守值）
</action>
<files>
- pipeline/queue/scheduler.py (new)
</files>
<verify>
<automated>pytest -q tests/test_scheduler_gpu_lock.py tests/test_scheduler_integration.py -x</automated>
</verify>
<done>
- pipeline/queue/scheduler.py 包含 class TaskScheduler:
- pipeline/queue/scheduler.py 包含 async def start(self)
- pipeline/queue/scheduler.py 包含 async def stop(self)
- pipeline/queue/scheduler.py 包含 async def _poll_loop(self)
- pipeline/queue/scheduler.py 包含 async def _process_next(self)
- pipeline/queue/scheduler.py 包含 async def _execute_download_stage(
- pipeline/queue/scheduler.py 包含 DL_MAX_CONCURRENT = 2
- pipeline/queue/scheduler.py 包含 _dl_semaphore
- pipeline/queue/scheduler.py 包含 from gpu_lock import acquire_gpu_lock, release_gpu_lock
- pipeline/queue/scheduler.py 包含 GPU_STAGES = {StageType.TRANSCRIBE}
- pipeline/queue/scheduler.py 包含 POLL_INTERVAL = 5
- pipeline/queue/scheduler.py 包含 asyncio.to_thread
- pipeline/queue/scheduler.py 包含 repo.claim_next_stage()
- pipeline/queue/scheduler.py 包含 repo.complete_stage(
- pipeline/queue/scheduler.py 包含 repo.mark_stage_for_retry(
- pipeline/queue/scheduler.py 包含 enqueue_next_stage(session, stage_task)
- pipeline/queue/scheduler.py 包含 backoff_seconds=backoff_delay
</done>
</task>

<task id="03-02">
<title>實作 QUEUE-02 及排程器整合的完整測試</title>
<read_first>
- tests/test_scheduler_gpu_lock.py (stub)
- pipeline/queue/scheduler.py (TaskScheduler)
- pipeline/queue/repository.py (TaskRepository API)
- pipeline/queue/models.py (所有模型)
- tests/conftest.py (db_engine / db_session fixture)
</read_first>
<action>
替換 `tests/test_scheduler_gpu_lock.py` 中的 stub 為完整實作，並建立 `tests/test_scheduler_integration.py`：

**`tests/test_scheduler_gpu_lock.py`** — QUEUE-02 測試:

```python
def test_single_gpu_enforced(db_session):
    """QUEUE-02: 一個 transcribe stage running 時，claim 不會取到第二個 transcribe。"""
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.models import TaskStatus, StageType, TaskSource

    repo = TaskRepository(db_session)
    t1 = repo.create_task(title="Task 1", video_id="v1")
    t2 = repo.create_task(title="Task 2", video_id="v2")

    s1 = repo.create_stage_task(t1.id, StageType.TRANSCRIBE, source=TaskSource.INTERNAL)
    s2 = repo.create_stage_task(t2.id, StageType.TRANSCRIBE, source=TaskSource.INTERNAL)

    # Claim 第一個
    claimed1 = repo.claim_next_stage(stage_filter=StageType.TRANSCRIBE)
    assert claimed1 is not None
    assert claimed1.status == TaskStatus.RUNNING

    # 驗證只有一個 running
    running = repo.get_running_stages(stage_filter=StageType.TRANSCRIBE)
    assert len(running) == 1

def test_non_gpu_stages_can_run_parallel(db_session):
    """QUEUE-02: 非 GPU stage (download) 可同時 running。"""
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.models import TaskStatus, StageType, TaskSource

    repo = TaskRepository(db_session)
    t1 = repo.create_task(title="Task 1", video_id="v1")
    t2 = repo.create_task(title="Task 2", video_id="v2")

    repo.create_stage_task(t1.id, StageType.DOWNLOAD, source=TaskSource.INTERNAL)
    repo.create_stage_task(t2.id, StageType.DOWNLOAD, source=TaskSource.INTERNAL)

    claimed1 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    claimed2 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)

    assert claimed1 is not None
    assert claimed2 is not None
    running = repo.get_running_stages(stage_filter=StageType.DOWNLOAD)
    assert len(running) == 2
```

**`tests/test_scheduler_integration.py`:**

```python
"""整合測試：排程器 + 佇列 + fan-out 端對端流程。"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from sqlmodel import Session
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from pipeline.queue.models import (
    Task, StageTask, StageType, TaskStatus, TaskSource,
)
from pipeline.queue.repository import TaskRepository
from pipeline.queue.scheduler import TaskScheduler
from pipeline.queue.stage_runner import create_initial_stages, enqueue_next_stage


@pytest.fixture
def integration_engine():
    """整合測試用 engine（in-memory）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def integration_session(integration_engine):
    """整合測試用 Session。"""
    with Session(integration_engine) as session:
        yield session


def test_scheduler_processes_stage_with_mock_executor(integration_session):
    """排程器可以 claim 並執行一個 stage（使用 mock executor）。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(
        title="Integration test",
        video_id="int_test_001",
        source=TaskSource.INTERNAL,
    )
    create_initial_stages(integration_session, task, StageType.DOWNLOAD)

    mock_executor = MagicMock()
    executors = {StageType.DOWNLOAD: mock_executor}

    scheduler = TaskScheduler(
        session_factory=lambda: integration_session,
        stage_executors=executors,
        poll_interval=1,
    )

    asyncio.get_event_loop().run_until_complete(scheduler._process_next())
    assert mock_executor.call_count == 1


def test_enqueue_creates_task_and_stages(integration_session):
    """建立任務 + 初始 stage，驗證 DB 狀態正確。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(
        title="佛教公案 001",
        video_id="vid_e2e_001",
        playlist_id="pl_001",
        source=TaskSource.INTERNAL,
    )
    dl_stage = create_initial_stages(integration_session, task, StageType.DOWNLOAD)

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.source == TaskSource.INTERNAL
    assert dl_stage.task_id == task.id
    assert dl_stage.stage == StageType.DOWNLOAD
    assert dl_stage.status == TaskStatus.PENDING
    assert repo.count_pending_stages() == 1


def test_complete_stage_triggers_fanout(integration_session):
    """完成 download stage 後自動建立 transcribe stage。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(title="Fanout", video_id="fanout_e2e")
    dl = create_initial_stages(integration_session, task, StageType.DOWNLOAD)

    repo.complete_stage(dl.id)
    integration_session.refresh(dl)

    next_stage = enqueue_next_stage(integration_session, dl)
    assert next_stage is not None
    assert next_stage.stage == StageType.TRANSCRIBE
    assert next_stage.status == TaskStatus.PENDING
    assert repo.count_pending_stages() == 1


@patch("gpu_lock.acquire_gpu_lock", return_value=None)
def test_scheduler_returns_stage_when_gpu_busy(
    mock_gpu_lock,
    integration_session,
):
    """GPU 忙碌時 transcribe stage 退回 pending。"""
    repo = TaskRepository(integration_session)
    task = repo.create_task(title="GPU busy test", video_id="gpubusy1")
    create_initial_stages(integration_session, task, StageType.TRANSCRIBE)

    executors = {StageType.TRANSCRIBE: MagicMock()}
    scheduler = TaskScheduler(
        session_factory=lambda: integration_session,
        stage_executors=executors,
        poll_interval=1,
    )

    asyncio.get_event_loop().run_until_complete(scheduler._process_next())

    assert executors[StageType.TRANSCRIBE].call_count == 0

    stages = repo.get_stages_for_task(task.id)
    assert len(stages) == 1
    assert stages[0].status == TaskStatus.PENDING


def test_download_concurrency_limit(integration_session):
    """下載最多 2 併行，超過時退回 pending。"""
    repo = TaskRepository(integration_session)

    # 建立 3 個 download tasks
    tasks = []
    for i in range(3):
        t = repo.create_task(title=f"DL {i}", video_id=f"dl_{i}")
        create_initial_stages(integration_session, t, StageType.DOWNLOAD)
        tasks.append(t)

    # Claim 前 2 個
    claimed1 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    claimed2 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    assert claimed1 is not None
    assert claimed2 is not None

    # 已有 2 個 running download
    running = repo.get_running_stages(stage_filter=StageType.DOWNLOAD)
    assert len(running) == 2

    # 第 3 個仍是 pending（排程器會在 _execute_download_stage 中退回）
    stages = repo.get_stages_for_task(tasks[2].id)
    assert any(s.status == TaskStatus.PENDING for s in stages)
```

移除所有 `pytest.skip("Stub ...")` 行，確保全部是可執行的真正測試。
</action>
<files>
- tests/test_scheduler_gpu_lock.py (modify — replace stubs)
- tests/test_scheduler_integration.py (new)
</files>
<verify>
<automated>pytest -q tests/test_scheduler_gpu_lock.py tests/test_scheduler_integration.py -x</automated>
</verify>
<done>
- tests/test_scheduler_gpu_lock.py 不包含 pytest.skip("Stub
- tests/test_scheduler_gpu_lock.py 包含 def test_single_gpu_enforced(
- tests/test_scheduler_gpu_lock.py 包含 def test_non_gpu_stages_can_run_parallel(
- tests/test_scheduler_integration.py 包含 def test_scheduler_processes_stage_with_mock_executor(
- tests/test_scheduler_integration.py 包含 def test_enqueue_creates_task_and_stages(
- tests/test_scheduler_integration.py 包含 def test_complete_stage_triggers_fanout(
- tests/test_scheduler_integration.py 包含 def test_scheduler_returns_stage_when_gpu_busy(
- tests/test_scheduler_integration.py 包含 def test_download_concurrency_limit(
- 執行 pytest -q 結果全部 passed
</done>
</task>

## Verification

```bash
# Scheduler 結構正確
grep "class TaskScheduler" pipeline/queue/scheduler.py
grep "acquire_gpu_lock" pipeline/queue/scheduler.py
grep "DL_MAX_CONCURRENT" pipeline/queue/scheduler.py
grep "_dl_semaphore" pipeline/queue/scheduler.py

# 測試
pytest -q tests/test_scheduler_gpu_lock.py tests/test_scheduler_integration.py
```

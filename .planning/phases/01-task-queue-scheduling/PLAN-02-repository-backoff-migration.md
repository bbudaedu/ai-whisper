---
plan: "02"
title: "Repository 層、退避策略與遷移 Fallback"
phase: 1
wave: 1
depends_on:
  - "01"
requirements:
  - QUEUE-01
  - QUEUE-03
  - QUEUE-05
must_haves:
  truths:
    - Repository 提供原子 claim 操作，避免雙重執行
    - claim_next_stage 過濾 next_retry_at 未到時間的任務
    - Internal 任務優先於 external 任務被 claim（QUEUE-03）
    - 失敗 stage 按指數退避自動重試，寫入 next_retry_at 欄位，超過 max_retries 標記 failed（QUEUE-05）
    - processed_videos.json fallback 讀取機制正常運作
    - 父任務/子任務建立與查詢
  artifacts:
    - pipeline/queue/repository.py
    - pipeline/queue/backoff.py
    - pipeline/queue/migration.py
    - tests/test_task_queue.py (stubs replaced with real tests)
    - tests/test_scheduler_priority.py (stubs replaced)
    - tests/test_retry_policy.py (stubs replaced)
    - tests/test_migration_fallback.py
  key_links:
    - "pipeline/queue/repository.py (TaskRepository) -> pipeline/queue/models.py (Task, StageTask)"
    - "pipeline/queue/repository.py (mark_stage_for_retry) -> pipeline/queue/backoff.py (calculate_backoff)"
    - "pipeline/queue/migration.py (is_video_processed) -> pipeline/queue/repository.py (get_task_by_video_id)"
files_modified:
  - pipeline/queue/repository.py
  - pipeline/queue/backoff.py
  - pipeline/queue/migration.py
  - tests/test_task_queue.py
  - tests/test_scheduler_priority.py
  - tests/test_retry_policy.py
  - tests/test_migration_fallback.py
autonomous: true
---

# Plan 02: Repository 層、退避策略與遷移 Fallback

## Goal
實作 DB 存取層（原子 claim、佇列查詢、優先權排序）、指數退避重試策略（含 next_retry_at 排程）、processed_videos.json fallback 讀取，以及父任務/子任務建立流程，涵蓋 QUEUE-01、03、05 的核心邏輯。

## Tasks

<task id="02-01">
<title>實作 Repository 層 (repository.py)</title>
<read_first>
- pipeline/queue/models.py (Task / StageTask / TaskStatus / TaskSource / StageType 定義，含 output_payload / next_retry_at)
- pipeline/queue/database.py (get_engine / get_session / create_db_and_tables)
- .planning/phases/01-task-queue-scheduling/01-RESEARCH.md §Pattern 2 (原子 claim 模式)
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md §排程與優先權機制
</read_first>
<action>
建立 `pipeline/queue/repository.py`，提供以下功能：

```python
"""Task queue repository — DB 存取與原子操作。"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select, col
from sqlalchemy import update

from pipeline.queue.models import (
    Task, StageTask, TaskStatus, TaskSource, StageType,
)

logger = logging.getLogger(__name__)


class TaskRepository:
    """任務佇列的 DB 存取層。"""

    def __init__(self, session: Session):
        self.session = session

    # ── 任務建立 ──────────────────────────────────

    def create_task(
        self,
        title: str,
        video_id: str,
        playlist_id: str = "",
        source: TaskSource = TaskSource.INTERNAL,
        parent_task_id: Optional[int] = None,
        max_retries: int = 3,
    ) -> Task:
        """建立新任務（pending 狀態）。"""
        priority = 10 if source == TaskSource.INTERNAL else 0
        task = Task(
            title=title,
            video_id=video_id,
            playlist_id=playlist_id,
            source=source,
            status=TaskStatus.PENDING,
            priority=priority,
            max_retries=max_retries,
            parent_task_id=parent_task_id,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def create_playlist_parent_task(
        self,
        playlist_id: str,
        playlist_title: str,
        source: TaskSource = TaskSource.INTERNAL,
    ) -> Task:
        """建立播放清單父任務。

        父任務本身不執行 stage，而是作為子任務的容器。
        子任務（每集影片）透過 parent_task_id 關聯。
        """
        return self.create_task(
            title=playlist_title,
            video_id="",  # 父任務無對應單一影片
            playlist_id=playlist_id,
            source=source,
            parent_task_id=None,
        )

    def create_child_task(
        self,
        parent_task_id: int,
        title: str,
        video_id: str,
        playlist_id: str = "",
        source: TaskSource = TaskSource.INTERNAL,
        max_retries: int = 3,
    ) -> Task:
        """建立子任務（關聯到父任務）。"""
        return self.create_task(
            title=title,
            video_id=video_id,
            playlist_id=playlist_id,
            source=source,
            parent_task_id=parent_task_id,
            max_retries=max_retries,
        )

    def create_stage_task(
        self,
        task_id: int,
        stage: StageType,
        source: TaskSource = TaskSource.INTERNAL,
        priority: int = 0,
        max_retries: int = 3,
    ) -> StageTask:
        """為指定 task 建立 stage 子任務。"""
        if source == TaskSource.INTERNAL:
            priority = max(priority, 10)
        stage_task = StageTask(
            task_id=task_id,
            stage=stage,
            status=TaskStatus.PENDING,
            source=source,
            priority=priority,
            max_retries=max_retries,
        )
        self.session.add(stage_task)
        self.session.commit()
        self.session.refresh(stage_task)
        return stage_task

    # ── 原子 Claim ──────────────────────────────────

    def claim_next_stage(
        self,
        stage_filter: Optional[StageType] = None,
    ) -> Optional[StageTask]:
        """原子地 claim 下一個可執行的 stage task。

        排序邏輯：
        1. source=internal (priority DESC) 優先
        2. 同 source 內按 created_at ASC
        3. 可選擇性過濾特定 stage type
        4. 排除 next_retry_at 未到時間的任務（退避中）

        使用 SELECT ... FOR UPDATE 模式（SQLite 透過 begin immediate）。
        """
        now = datetime.utcnow()
        query = (
            select(StageTask)
            .where(StageTask.status == TaskStatus.PENDING)
            .where(
                # next_retry_at 為 None（首次）或已到時間
                (StageTask.next_retry_at == None) | (StageTask.next_retry_at <= now)  # noqa: E711
            )
        )
        if stage_filter is not None:
            query = query.where(StageTask.stage == stage_filter)

        query = query.order_by(
            col(StageTask.priority).desc(),
            col(StageTask.created_at).asc(),
        ).limit(1)

        stage_task = self.session.exec(query).first()
        if stage_task is None:
            return None

        # 原子更新：只有 status 仍是 pending 才會成功
        stmt = (
            update(StageTask)
            .where(StageTask.id == stage_task.id)
            .where(StageTask.status == TaskStatus.PENDING)
            .values(status=TaskStatus.RUNNING, started_at=now, updated_at=now)
        )
        result = self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

        if result.rowcount == 0:  # type: ignore[union-attr]
            return None  # 被其他 worker 搶先 claim

        self.session.refresh(stage_task)
        return stage_task

    # ── Stage 輸出儲存 ──────────────────────────────────

    def save_stage_output(self, stage_task_id: int, output: dict) -> None:
        """儲存 stage 的執行結果至 output_payload。"""
        stage = self.session.get(StageTask, stage_task_id)
        if stage is None:
            return
        stage.set_output(output)
        stage.updated_at = datetime.utcnow()
        self.session.commit()

    def get_previous_stage_output(self, task_id: int, stage: StageType) -> dict:
        """取得同一 task 的前一 stage 的輸出。

        用於建構下一 stage 的 context。依 STAGE_ORDER 查找前一個
        已完成 stage 的 output_payload。
        """
        from pipeline.queue.stage_runner import STAGE_ORDER
        stage_idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else -1
        if stage_idx <= 0:
            return {}  # download 是第一個，無前序

        prev_stage_type = STAGE_ORDER[stage_idx - 1]
        query = (
            select(StageTask)
            .where(StageTask.task_id == task_id)
            .where(StageTask.stage == prev_stage_type)
            .where(StageTask.status == TaskStatus.DONE)
            .order_by(col(StageTask.completed_at).desc())
            .limit(1)
        )
        prev = self.session.exec(query).first()
        if prev is None:
            return {}
        return prev.get_output()

    # ── 狀態更新 ──────────────────────────────────

    def complete_stage(self, stage_task_id: int) -> None:
        """標記 stage 為 done。"""
        now = datetime.utcnow()
        stmt = (
            update(StageTask)
            .where(StageTask.id == stage_task_id)
            .values(status=TaskStatus.DONE, completed_at=now, updated_at=now)
        )
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

    def fail_stage(self, stage_task_id: int, error_message: str) -> None:
        """標記 stage 為 failed，記錄錯誤訊息。"""
        now = datetime.utcnow()
        stmt = (
            update(StageTask)
            .where(StageTask.id == stage_task_id)
            .values(
                status=TaskStatus.FAILED,
                error_message=error_message,
                completed_at=now,
                updated_at=now,
            )
        )
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

    def mark_stage_for_retry(
        self, stage_task_id: int, error_message: str, backoff_seconds: float = 0
    ) -> bool:
        """嘗試重試 stage：增加 retry_count，設定 next_retry_at，若未超過 max_retries 則重設為 pending。

        Args:
            stage_task_id: stage 任務 ID
            error_message: 錯誤訊息
            backoff_seconds: 退避延遲秒數（由 calculate_backoff 計算）

        Returns:
            True 表示已安排重試，False 表示已超過 max_retries（標記為 failed）。
        """
        from datetime import timedelta
        stage = self.session.get(StageTask, stage_task_id)
        if stage is None:
            return False

        stage.retry_count += 1
        stage.error_message = error_message
        stage.updated_at = datetime.utcnow()

        if stage.retry_count >= stage.max_retries:
            stage.status = TaskStatus.FAILED
            stage.completed_at = datetime.utcnow()
            self.session.commit()
            return False

        stage.status = TaskStatus.PENDING
        stage.started_at = None
        if backoff_seconds > 0:
            stage.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
        else:
            stage.next_retry_at = None
        self.session.commit()
        return True

    # ── 父任務狀態 ──────────────────────────────────

    def check_and_update_parent_status(self, parent_task_id: int) -> None:
        """檢查父任務的所有子任務，更新父任務狀態。

        - 若所有子任務都是 DONE → 父任務 DONE
        - 若任一子任務 FAILED 且無 pending/running → 父任務 FAILED
        - 否則保持 RUNNING
        """
        children = self.get_child_tasks(parent_task_id)
        if not children:
            return

        statuses = {c.status for c in children}
        if statuses == {TaskStatus.DONE}:
            self.update_task_status(parent_task_id, TaskStatus.DONE)
        elif TaskStatus.FAILED in statuses and TaskStatus.PENDING not in statuses and TaskStatus.RUNNING not in statuses:
            self.update_task_status(parent_task_id, TaskStatus.FAILED)
        elif TaskStatus.RUNNING in statuses or TaskStatus.PENDING in statuses:
            self.update_task_status(parent_task_id, TaskStatus.RUNNING)

    # ── 查詢 ──────────────────────────────────

    def get_running_stages(
        self,
        stage_filter: Optional[StageType] = None,
    ) -> list[StageTask]:
        """查詢目前 running 的 stage tasks。"""
        query = select(StageTask).where(StageTask.status == TaskStatus.RUNNING)
        if stage_filter is not None:
            query = query.where(StageTask.stage == stage_filter)
        return list(self.session.exec(query).all())

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """根據 ID 取得 Task。"""
        return self.session.get(Task, task_id)

    def get_task_by_video_id(self, video_id: str) -> Optional[Task]:
        """根據 video_id 查詢任務（用於 fallback 查詢）。"""
        query = select(Task).where(Task.video_id == video_id).limit(1)
        return self.session.exec(query).first()

    def get_child_tasks(self, parent_task_id: int) -> list[Task]:
        """取得父任務的所有子任務。"""
        query = (
            select(Task)
            .where(Task.parent_task_id == parent_task_id)
            .order_by(col(Task.created_at).asc())
        )
        return list(self.session.exec(query).all())

    def get_stages_for_task(self, task_id: int) -> list[StageTask]:
        """取得某 Task 的所有 stage tasks。"""
        query = (
            select(StageTask)
            .where(StageTask.task_id == task_id)
            .order_by(col(StageTask.created_at).asc())
        )
        return list(self.session.exec(query).all())

    def count_pending_stages(self) -> int:
        """計算 pending stage 數量。"""
        query = select(StageTask).where(StageTask.status == TaskStatus.PENDING)
        return len(list(self.session.exec(query).all()))

    def update_task_status(self, task_id: int, status: TaskStatus) -> None:
        """更新 Task 的整體狀態。"""
        now = datetime.utcnow()
        values: dict = {"status": status, "updated_at": now}
        if status in (TaskStatus.DONE, TaskStatus.FAILED):
            values["completed_at"] = now
        stmt = update(Task).where(Task.id == task_id).values(**values)
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()
```

重點設計：
- `claim_next_stage` 以 `priority DESC, created_at ASC` 排序，internal 任務 priority=10 > external priority=0
- `claim_next_stage` **過濾 `next_retry_at`**：只 claim `next_retry_at IS NULL OR next_retry_at <= now()` 的任務
- 原子 claim 使用 `UPDATE ... WHERE status='pending'` 搭配 rowcount 檢查
- `mark_stage_for_retry` 接受 `backoff_seconds` 參數，計算 `next_retry_at` 寫入 DB
- `save_stage_output` / `get_previous_stage_output` 支援 stage 間資料傳遞
- `create_playlist_parent_task` / `create_child_task` 支援父任務/子任務模型
- `check_and_update_parent_status` 聚合子任務狀態更新父任務
</action>
<files>
- pipeline/queue/repository.py (new)
</files>
<verify>
<automated>pytest -q tests/test_task_queue.py tests/test_scheduler_priority.py -x</automated>
</verify>
<done>
- pipeline/queue/repository.py 包含 class TaskRepository:
- pipeline/queue/repository.py 包含 def create_task(
- pipeline/queue/repository.py 包含 def create_playlist_parent_task(
- pipeline/queue/repository.py 包含 def create_child_task(
- pipeline/queue/repository.py 包含 def create_stage_task(
- pipeline/queue/repository.py 包含 def claim_next_stage(
- claim_next_stage 包含 next_retry_at 過濾條件
- pipeline/queue/repository.py 包含 def complete_stage(
- pipeline/queue/repository.py 包含 def fail_stage(
- pipeline/queue/repository.py 包含 def mark_stage_for_retry( 含 backoff_seconds 參數
- pipeline/queue/repository.py 包含 def save_stage_output(
- pipeline/queue/repository.py 包含 def get_previous_stage_output(
- pipeline/queue/repository.py 包含 def get_running_stages(
- pipeline/queue/repository.py 包含 def get_child_tasks(
- pipeline/queue/repository.py 包含 def check_and_update_parent_status(
- pipeline/queue/repository.py 包含 col(StageTask.priority).desc()
- pipeline/queue/repository.py 包含 result.rowcount == 0
</done>
</task>

<task id="02-02">
<title>實作指數退避模組 (backoff.py)</title>
<read_first>
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md §失敗與重試行為 (指數退避、預設 3 次)
- pipeline/queue/models.py (StageTask.retry_count / max_retries / next_retry_at 欄位)
</read_first>
<action>
建立 `pipeline/queue/backoff.py`：

```python
"""指數退避計算模組。"""
import random


def calculate_backoff(
    retry_count: int,
    base_delay: float = 5.0,
    max_delay: float = 300.0,
    jitter: bool = True,
) -> float:
    """計算指數退避延遲秒數。

    delay = min(base_delay * 2^retry_count, max_delay) + jitter

    Args:
        retry_count: 已重試次數（0-based，第一次重試 retry_count=0）
        base_delay: 基礎延遲（秒）
        max_delay: 最大延遲（秒）
        jitter: 是否加入隨機抖動（避免重試雪崩）

    Returns:
        延遲秒數
    """
    delay = min(base_delay * (2 ** retry_count), max_delay)
    if jitter:
        delay += random.uniform(0, delay * 0.1)
    return delay


def should_retry(retry_count: int, max_retries: int) -> bool:
    """判斷是否應該重試。

    Args:
        retry_count: 已重試次數
        max_retries: 最大重試次數

    Returns:
        True 表示還可以重試
    """
    return retry_count < max_retries
```

參數選擇理由：
- `base_delay=5.0` 秒：避免太快重試造成連續失敗
- `max_delay=300.0` 秒（5 分鐘）：避免等待過久
- `jitter=True`：避免多任務同時重試時的競爭
</action>
<files>
- pipeline/queue/backoff.py (new)
</files>
<verify>
<automated>pytest -q tests/test_retry_policy.py::test_retry_backoff tests/test_retry_policy.py::test_backoff_max_cap tests/test_retry_policy.py::test_should_retry -x</automated>
</verify>
<done>
- pipeline/queue/backoff.py 包含 def calculate_backoff(
- pipeline/queue/backoff.py 包含 def should_retry(
- pipeline/queue/backoff.py 包含 base_delay: float = 5.0
- pipeline/queue/backoff.py 包含 max_delay: float = 300.0
- pipeline/queue/backoff.py 包含 2 ** retry_count
</done>
</task>

<task id="02-03">
<title>實作 processed_videos.json 遷移 fallback (migration.py)</title>
<read_first>
- auto_youtube_whisper.py (load_processed_videos / save_processed_videos / STATE_FILE)
- pipeline/queue/models.py (Task / TaskStatus)
- pipeline/queue/repository.py (TaskRepository.get_task_by_video_id / create_task)
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md §佇列持久化策略（漸進遷移決策）
</read_first>
<action>
建立 `pipeline/queue/migration.py`，提供 processed_videos.json 的 fallback 讀取：

```python
"""processed_videos.json 遷移 fallback 模組。

策略（來自 CONTEXT.md 鎖定決策）：
- 新任務寫入 SQLite
- 查詢影片是否已處理時，先查 SQLite，若無再 fallback 讀 JSON
- 不修改現有 JSON 寫入邏輯（auto_youtube_whisper.py 持續寫入）
- 雙軌並行至 Phase 2 完全遷移
"""
import json
import logging
import os
from typing import Optional

from sqlmodel import Session

from pipeline.queue.models import Task, TaskStatus
from pipeline.queue.repository import TaskRepository

logger = logging.getLogger(__name__)

# 預設 JSON 路徑與 auto_youtube_whisper.py 一致
_DEFAULT_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "processed_videos.json",
)


def is_video_processed(
    video_id: str,
    session: Session,
    json_path: str = _DEFAULT_JSON_PATH,
) -> bool:
    """檢查影片是否已處理（SQLite 優先，JSON fallback）。

    Args:
        video_id: YouTube 影片 ID
        session: SQLModel Session
        json_path: processed_videos.json 路徑

    Returns:
        True 如果影片已在 SQLite 或 JSON 中標記為完成
    """
    # 1. 先查 SQLite
    repo = TaskRepository(session)
    task = repo.get_task_by_video_id(video_id)
    if task is not None and task.status == TaskStatus.DONE:
        return True

    # 2. Fallback: 讀取 JSON
    json_data = _load_json_fallback(json_path)
    if video_id in json_data:
        logger.debug(f"影片 {video_id} 在 JSON fallback 中找到（尚未遷移至 SQLite）")
        return True

    return False


def get_processed_video_info(
    video_id: str,
    session: Session,
    json_path: str = _DEFAULT_JSON_PATH,
) -> Optional[dict]:
    """取得影片的處理資訊（SQLite 優先，JSON fallback）。

    Returns:
        處理資訊 dict 或 None
    """
    # 1. 先查 SQLite
    repo = TaskRepository(session)
    task = repo.get_task_by_video_id(video_id)
    if task is not None:
        return {
            "title": task.title,
            "status": task.status.value,
            "processed_at": task.completed_at.isoformat() if task.completed_at else None,
            "source": "sqlite",
        }

    # 2. Fallback: JSON
    json_data = _load_json_fallback(json_path)
    if video_id in json_data:
        info = json_data[video_id]
        info["source"] = "json_fallback"
        return info

    return None


def _load_json_fallback(json_path: str) -> dict:
    """載入 processed_videos.json（含錯誤處理）。"""
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"無法讀取 {json_path}: {e}")
        return {}
```

設計重點：
- 遵循 CONTEXT.md 決策：「新任務寫入 SQLite，舊資料按需讀取 JSON fallback」
- `is_video_processed` 先查 SQLite，若無結果再讀 JSON
- 不修改現有 `auto_youtube_whisper.py` 的 `save_processed_videos` 邏輯
- 雙軌並行直到 Phase 2 完全遷移
</action>
<files>
- pipeline/queue/migration.py (new)
</files>
<verify>
<automated>pytest -q tests/test_migration_fallback.py -x</automated>
</verify>
<done>
- pipeline/queue/migration.py 包含 def is_video_processed(
- pipeline/queue/migration.py 包含 def get_processed_video_info(
- pipeline/queue/migration.py 包含 def _load_json_fallback(
- pipeline/queue/migration.py 包含 processed_videos.json
- is_video_processed 先查 SQLite 再 fallback JSON
- _load_json_fallback 含 json.JSONDecodeError 錯誤處理
</done>
</task>

## Verification

```bash
# Repository API
grep -c "def " pipeline/queue/repository.py  # 至少 14 個函式

# 退避排程
grep "next_retry_at" pipeline/queue/repository.py
grep "backoff_seconds" pipeline/queue/repository.py

# Migration fallback
grep "is_video_processed" pipeline/queue/migration.py
grep "processed_videos.json" pipeline/queue/migration.py

# 測試
pytest -q tests/test_task_queue.py tests/test_scheduler_priority.py tests/test_retry_policy.py tests/test_migration_fallback.py
```

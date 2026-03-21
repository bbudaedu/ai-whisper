"""Stage 執行器 — 負責執行 stage 並觸發 fan-out（下一 stage）。"""
import logging
from typing import Optional

from sqlmodel import Session

from pipeline.queue.models import StageTask, StageType, TaskStatus, Task
from pipeline.queue.repository import TaskRepository

logger = logging.getLogger(__name__)

STAGE_ORDER: list[StageType] = [
    StageType.DOWNLOAD,
    StageType.TRANSCRIBE,
    StageType.PROOFREAD,
    StageType.POSTPROCESS,
]

NEXT_STAGE: dict[StageType, Optional[StageType]] = {}
for i, stage in enumerate(STAGE_ORDER):
    if i + 1 < len(STAGE_ORDER):
        NEXT_STAGE[stage] = STAGE_ORDER[i + 1]
    else:
        NEXT_STAGE[stage] = None


def get_next_stage(current_stage: StageType) -> Optional[StageType]:
    """取得下一個 stage。"""
    return NEXT_STAGE.get(current_stage)


def enqueue_next_stage(
    session: Session,
    completed_stage: StageTask,
) -> Optional[StageTask]:
    """Stage 完成後自動建立下一 stage 的任務。"""
    next_stage_type = get_next_stage(completed_stage.stage)

    if next_stage_type is None:
        repo = TaskRepository(session)
        repo.update_task_status(completed_stage.task_id, TaskStatus.DONE)
        logger.info(
            f"Task #{completed_stage.task_id} 所有 stage 完成，狀態更新為 DONE"
        )

        task = repo.get_task_by_id(completed_stage.task_id)
        if task and task.parent_task_id:
            repo.check_and_update_parent_status(task.parent_task_id)

        return None

    repo = TaskRepository(session)
    new_stage = repo.create_stage_task(
        task_id=completed_stage.task_id,
        stage=next_stage_type,
        source=completed_stage.source,
        priority=completed_stage.priority,
        max_retries=completed_stage.max_retries,
    )
    logger.info(
        f"Fan-out: stage #{completed_stage.id} ({completed_stage.stage}) 完成 → "
        f"建立 stage #{new_stage.id} ({next_stage_type})"
    )
    return new_stage


def create_initial_stages(
    session: Session,
    task: Task,
    start_stage: StageType = StageType.DOWNLOAD,
) -> StageTask:
    """為新任務建立初始 stage task。"""
    repo = TaskRepository(session)
    stage = repo.create_stage_task(
        task_id=task.id,
        stage=start_stage,
        source=task.source,
        priority=task.priority,
        max_retries=task.max_retries,
    )
    logger.info(
        f"Task #{task.id} 建立初始 stage: {start_stage} (stage #{stage.id})"
    )
    return stage


def build_context_for_stage(
    session: Session,
    stage_task: StageTask,
) -> dict:
    """為 stage 建構執行 context。"""
    repo = TaskRepository(session)
    task = repo.get_task_by_id(stage_task.task_id)
    if task is None:
        raise RuntimeError(f"Task #{stage_task.task_id} not found")

    context: dict = {
        "video_id": task.video_id,
        "title": task.title,
        "playlist_id": task.playlist_id,
        "playlist_config": {},
    }

    prev_output = repo.get_previous_stage_output(task.id, stage_task.stage)
    context.update(prev_output)

    return context

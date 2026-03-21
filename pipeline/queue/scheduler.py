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

StageExecutor = Callable[[StageTask], None]

GPU_STAGES = {StageType.TRANSCRIBE}
DL_MAX_CONCURRENT = 2
POLL_INTERVAL = 5


class TaskScheduler:
    """Polling-based 排程器。"""

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
            stage_task = repo.claim_next_stage()
            if stage_task is None:
                return

            logger.info(
                f"已 claim stage task #{stage_task.id}: "
                f"stage={stage_task.stage}, task_id={stage_task.task_id}, "
                f"source={stage_task.source}"
            )

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
        running_downloads = repo.get_running_stages(stage_filter=StageType.DOWNLOAD)
        other_running = [s for s in running_downloads if s.id != stage_task.id]
        if len(other_running) >= DL_MAX_CONCURRENT:
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
            executor = self.stage_executors.get(stage_task.stage)
            if executor is None:
                raise RuntimeError(f"無 executor 註冊給 stage: {stage_task.stage}")

            await asyncio.to_thread(executor, stage_task)

            repo.complete_stage(stage_task.id)
            logger.info(f"Stage #{stage_task.id} ({stage_task.stage}) 完成")

            from pipeline.queue.stage_runner import enqueue_next_stage

            session.refresh(stage_task)
            enqueue_next_stage(session, stage_task)

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Stage #{stage_task.id} ({stage_task.stage}) 執行失敗: {error_msg}"
            )

            if should_retry(stage_task.retry_count, stage_task.max_retries):
                backoff_delay = calculate_backoff(stage_task.retry_count)
                retried = repo.mark_stage_for_retry(
                    stage_task.id, error_msg, backoff_seconds=backoff_delay
                )
                if retried:
                    logger.info(
                        f"Stage #{stage_task.id} 排入重試 "
                        f"(retry {stage_task.retry_count + 1}/{stage_task.max_retries}, "
                        f"退避 {backoff_delay:.1f}s, next_retry_at 已設定)"
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

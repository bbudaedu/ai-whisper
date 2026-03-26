import asyncio
import logging
from datetime import datetime
from typing import Callable

from sqlmodel import Session, select, func
from pipeline.queue.models import PlaylistRecord, Task, TaskStatus, TaskSource
from pipeline.queue.repository import TaskRepository
from pipeline.queue.stage_runner import create_initial_stages

logger = logging.getLogger(__name__)

class PlaylistSyncWorker:
    """負責將狀態為 running 的播放清單同步並轉化為 Task，同時更新處理進度。"""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        sync_interval: int = 600,
    ):
        self.session_factory = session_factory
        self.sync_interval = sync_interval
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"PlaylistSyncWorker 已啟動 (間隔: {self.sync_interval}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PlaylistSyncWorker 已停止")

    async def _run_loop(self):
        while self._running:
            try:
                await self._sync_running_playlists()
            except Exception as e:
                logger.error(f"同步播放清單時發生錯誤: {e}", exc_info=True)
            await asyncio.sleep(self.sync_interval)

    async def _sync_running_playlists(self):
        """掃描資料庫中所有處於 running 狀態的播放清單並同步。"""
        with self.session_factory() as session:
            # 1. 取得需要同步的清單
            stmt = select(PlaylistRecord).where(
                PlaylistRecord.status == "running",
                PlaylistRecord.enabled == True
            )
            playlists = session.execute(stmt).scalars().all()

            if not playlists:
                return

            import auto_youtube_whisper
            repo = TaskRepository(session)

            for pl in playlists:
                logger.info(f"正在同步播放清單: {pl.name} ({pl.url})")
                try:
                    # 借用 auto_youtube_whisper 的邏輯來抓取影片
                    original_url = auto_youtube_whisper.PLAYLIST_URL
                    auto_youtube_whisper.PLAYLIST_URL = pl.url

                    # 抓取影片清單
                    videos = await asyncio.to_thread(auto_youtube_whisper.get_playlist_videos)

                    auto_youtube_whisper.PLAYLIST_URL = original_url # 還原

                    if not videos:
                        logger.warning(f"無法從 {pl.name} 取得影片資訊")
                        continue

                    # 2. 為每個影片建立任務 (若尚未存在)
                    new_tasks_count = 0
                    for v in videos:
                        video_id = v["id"]
                        title = v["title"]

                        # 檢查是否已存在該影片的任務 (不論來源)
                        existing_task = repo.get_task_by_video_id(video_id)
                        if not existing_task:
                            task = repo.create_task(
                                title=title,
                                video_id=video_id,
                                playlist_id=str(pl.id),
                                source=TaskSource.EXTERNAL,
                            )
                            task.requester = pl.requester
                            session.add(task)
                            session.commit()

                            create_initial_stages(session, task)
                            new_tasks_count += 1

                    # 3. 更新播放清單統計資訊
                    # 統計該播放清單下狀態為 DONE 的任務數
                    done_count_stmt = select(func.count(Task.id)).where(
                        Task.playlist_id == str(pl.id),
                        Task.status == TaskStatus.DONE
                    )
                    pl.processed_count = session.execute(done_count_stmt).scalar() or 0
                    pl.total_videos = len(videos)
                    pl.last_synced_at = datetime.utcnow()
                    pl.updated_at = datetime.utcnow()

                    session.add(pl)
                    session.commit()

                    if new_tasks_count > 0:
                        logger.info(f"播放清單 {pl.name} 新增了 {new_tasks_count} 個任務 (進度: {pl.processed_count}/{pl.total_videos})")
                    else:
                        logger.info(f"播放清單 {pl.name} 已同步 (進度: {pl.processed_count}/{pl.total_videos})")

                except Exception as e:
                    logger.error(f"同步清單 {pl.name} 失敗: {e}")
                    session.rollback()

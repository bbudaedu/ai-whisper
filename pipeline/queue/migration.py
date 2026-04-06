"""processed_videos.json 遷移 fallback 模組。

策略：
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

from pipeline.queue.models import TaskStatus
from pipeline.queue.repository import TaskRepository

logger = logging.getLogger(__name__)

_DEFAULT_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "processed_videos.json",
)


def is_video_processed(
    video_id: str,
    session: Session,
    json_path: str = _DEFAULT_JSON_PATH,
) -> bool:
    """檢查影片是否已處理（SQLite 優先，JSON fallback）。"""
    repo = TaskRepository(session)
    task = repo.get_task_by_video_id(video_id)
    if task is not None and task.status == TaskStatus.DONE:
        return True

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
    """取得影片的處理資訊（SQLite 優先，JSON fallback）。"""
    repo = TaskRepository(session)
    task = repo.get_task_by_video_id(video_id)
    if task is not None:
        return {
            "title": task.title,
            "status": task.status.value,
            "processed_at": task.completed_at.isoformat() if task.completed_at else None,
            "source": "sqlite",
        }

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

import json
from pipeline.queue.database import get_session
from pipeline.queue.repository import TaskRepository

def log_task_event(task_id: int, event_type: str, metadata: str | dict | None = None):
    """將任務事件紀錄至統一資料庫。"""
    with get_session() as session:
        repo = TaskRepository(session)
        if isinstance(metadata, str):
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                metadata_dict = {"raw": metadata}
        else:
            metadata_dict = metadata

        repo.add_event(task_id, event_type, metadata_dict)

def register_artifact(task_id: int, format: str, path: str):
    """將任務產出紀錄至統一資料庫。"""
    with get_session() as session:
        repo = TaskRepository(session)
        repo.add_artifact(task_id, format, path)

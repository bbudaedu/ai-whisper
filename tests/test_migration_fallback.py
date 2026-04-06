"""processed_videos.json fallback 測試。"""
import json
from pathlib import Path

from pipeline.queue.migration import is_video_processed, get_processed_video_info
from pipeline.queue.repository import TaskRepository
from pipeline.queue.models import TaskStatus


def test_fallback_to_json(db_session, tmp_path: Path):
    json_path = tmp_path / "processed_videos.json"
    json_path.write_text(json.dumps({"vid_json": {"title": "From JSON"}}), encoding="utf-8")

    assert is_video_processed("vid_json", db_session, json_path=str(json_path)) is True


def test_sqlite_preferred_over_json(db_session, tmp_path: Path):
    json_path = tmp_path / "processed_videos.json"
    json_path.write_text(json.dumps({"vid_sql": {"title": "From JSON"}}), encoding="utf-8")

    repo = TaskRepository(db_session)
    task = repo.create_task(title="From SQLite", video_id="vid_sql")
    repo.update_task_status(task.id, TaskStatus.DONE)

    info = get_processed_video_info("vid_sql", db_session, json_path=str(json_path))
    assert info is not None
    assert info["source"] == "sqlite"
    assert info["title"] == "From SQLite"

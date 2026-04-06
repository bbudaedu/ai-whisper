"""FastAPI lifespan + scheduler + API 端對端整合測試。"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

from pipeline.queue.models import StageType, TaskStatus
from pipeline.queue.repository import TaskRepository


_test_engine = None


def _reset_test_engine() -> None:
    global _test_engine
    if _test_engine is not None:
        _test_engine.dispose()
    _test_engine = None


def _test_get_engine():
    global _test_engine
    if _test_engine is None:
        _test_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return _test_engine


def _test_create_db_and_tables():
    engine = _test_get_engine()
    from pipeline.queue.models import Task, StageTask  # noqa: F401

    SQLModel.metadata.create_all(engine)


def _test_get_session() -> Session:
    engine = _test_get_engine()
    return Session(engine)


_mock_executors = {
    StageType.DOWNLOAD: MagicMock(),
    StageType.TRANSCRIBE: MagicMock(),
    StageType.PROOFREAD: MagicMock(),
    StageType.POSTPROCESS: MagicMock(),
}


@pytest.fixture(autouse=True)
def reset_mock_executors():
    for executor in _mock_executors.values():
        executor.reset_mock()
    yield


@pytest.fixture
def client():
    _reset_test_engine()
    _test_create_db_and_tables()
    with (
        patch("pipeline.queue.database.get_engine", _test_get_engine),
        patch("pipeline.queue.database.get_session", _test_get_session),
        patch("pipeline.queue.database.create_db_and_tables", _test_create_db_and_tables),
        patch("api_server.get_session", _test_get_session),
        patch("api_server.create_db_and_tables", _test_create_db_and_tables),
        patch(
            "pipeline.queue.scheduler.TaskScheduler.build_default_executors",
            return_value=_mock_executors,
        ),
        patch("pipeline.queue.scheduler.acquire_gpu_lock", return_value=999),
        patch("pipeline.queue.scheduler.release_gpu_lock", return_value=None),
    ):
        from api_server import app

        with TestClient(app) as client:
            yield client
    _reset_test_engine()


def _run_process_next():
    import api_server

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(api_server._scheduler._process_next())
    finally:
        loop.close()


def test_lifespan_starts_scheduler(client):
    import api_server

    assert api_server._scheduler is not None
    assert api_server._scheduler._running is True

    response = client.get("/api/queue/status")
    assert response.status_code == 200
    data = response.json()
    assert data["scheduler_running"] is True


def test_queue_submission_via_api(client):
    payload = {
        "action": "queue",
        "target": "test_vid_e2e",
        "title": "E2E Test Video",
        "source": "internal",
    }
    response = client.post("/api/task", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "queued"
    assert data["task_id"] is not None
    assert data["stage_id"] is not None
    assert data["video_id"] == "test_vid_e2e"

    status = client.get("/api/queue/status").json()
    assert status["pending_stages"] >= 1


def test_scheduler_claims_and_executes_via_api(client):
    payload = {
        "action": "queue",
        "target": "claim_vid_e2e",
        "title": "Claim Test Video",
        "source": "internal",
    }
    response = client.post("/api/task", json=payload)
    assert response.status_code == 200

    _run_process_next()

    assert _mock_executors[StageType.DOWNLOAD].call_count == 1


def test_fanout_after_execution_via_api(client):
    payload = {
        "action": "queue",
        "target": "fanout_vid_e2e",
        "title": "Fanout Test Video",
        "source": "internal",
    }
    response = client.post("/api/task", json=payload)
    assert response.status_code == 200
    data = response.json()

    _run_process_next()

    with _test_get_session() as session:
        repo = TaskRepository(session)
        stages = repo.get_stages_for_task(data["task_id"])

    stage_types = {stage.stage for stage in stages}
    assert StageType.DOWNLOAD in stage_types
    assert StageType.TRANSCRIBE in stage_types

    download_stage = next(stage for stage in stages if stage.stage == StageType.DOWNLOAD)
    transcribe_stage = next(stage for stage in stages if stage.stage == StageType.TRANSCRIBE)

    assert download_stage.status == TaskStatus.DONE
    assert transcribe_stage.status == TaskStatus.PENDING

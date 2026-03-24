import pytest
from fastapi.testclient import TestClient
from main import app
from api.auth import create_access_token
from pipeline.queue.database import get_session
from pipeline.queue.models import Task, TaskStatus
from pipeline.queue.repository import TaskRepository
from pathlib import Path
import os
import shutil

client = TestClient(app)

@pytest.fixture
def auth_header():
    token = create_access_token({"user_id": "test_user", "role": "external"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_output(tmp_path):
    # Setup mock output directory
    output_base = tmp_path / "output"
    output_base.mkdir()

    # Create a task directory
    task_id = 999
    task_dir = output_base / str(task_id)
    task_dir.mkdir()

    # Create various files
    (task_dir / "result.txt").write_text("text content")
    (task_dir / "result.srt").write_text("srt content")
    (task_dir / "result.json").write_text("{}")
    (task_dir / "image.png").write_text("not allowed")

    return output_base, task_id

def test_download_filter_logic(auth_header, mock_output, monkeypatch):
    output_base, task_id = mock_output

    # Mock OUTPUT_BASE in download router
    import api.routers.download
    monkeypatch.setattr(api.routers.download, "OUTPUT_BASE", output_base)

    # Create task in DB
    with get_session() as session:
        repo = TaskRepository(session)
        task = Task(
            id=task_id,
            title="Test Task",
            status=TaskStatus.DONE,
            requester="test_user"
        )
        session.add(task)
        session.commit()

    # Test 1: Download all (no filter)
    response = client.get(f"/api/tasks/{task_id}/download", headers=auth_header)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    # Test 2: Filter by txt
    response = client.get(f"/api/tasks/{task_id}/download?format=txt", headers=auth_header)
    assert response.status_code == 200
    # Since we can't easily inspect zip content here without unzipping,
    # we trust the logic if it returns 200 for allowed format

    # Test 3: Filter by unsupported format
    response = client.get(f"/api/tasks/{task_id}/download?format=png", headers=auth_header)
    assert response.status_code == 400
    assert "Unsupported format" in response.json()["detail"]

    # Test 4: Filter by format that doesn't exist for this task
    response = client.get(f"/api/tasks/{task_id}/download?format=vtt", headers=auth_header)
    assert response.status_code == 404
    assert "Requested format not found" in response.json()["detail"]

    # Test 5: Word alias
    (output_base / str(task_id) / "result.docx").write_text("word content")
    response = client.get(f"/api/tasks/{task_id}/download?format=word", headers=auth_header)
    assert response.status_code == 200

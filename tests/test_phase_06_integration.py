import pytest
from fastapi.testclient import TestClient
from main import app
from api.auth import create_access_token
from pipeline.queue.database import get_session
from pipeline.queue.models import Task, TaskStatus
from pipeline.queue.repository import TaskRepository

client = TestClient(app)

@pytest.fixture
def auth_header():
    token = create_access_token({"user_id": "test_user", "role": "external"})
    return {"Authorization": f"Bearer {token}"}

def test_api_prefix_consistency(auth_header):
    # Verify that history API works with the correct prefix
    response = client.get("/api/tasks/history", headers=auth_header)
    assert response.status_code == 200

def test_download_format_mapping(auth_header, monkeypatch, tmp_path):
    # Setup mock task and output
    task_id = 666
    output_base = tmp_path / "output"
    output_base.mkdir()
    task_dir = output_base / str(task_id)
    task_dir.mkdir()
    (task_dir / "result.docx").write_text("word content")
    (task_dir / "result.xlsx").write_text("excel content")

    import api.routers.download
    monkeypatch.setattr(api.routers.download, "OUTPUT_BASE", output_base)

    with get_session() as session:
        repo = TaskRepository(session)
        task = Task(id=task_id, title="Mapping Task", status=TaskStatus.DONE, requester="test_user")
        session.add(task)
        session.commit()

    # Test 'word' alias
    response = client.get(f"/api/tasks/{task_id}/download?format=word", headers=auth_header)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    # Test 'excel' alias
    response = client.get(f"/api/tasks/{task_id}/download?format=excel", headers=auth_header)
    assert response.status_code == 200

import pytest
from fastapi.testclient import TestClient
from main import app
from api.auth import create_access_token
from pipeline.queue.database import get_session
from pipeline.queue.models import Task, TaskStatus, TaskEvent, TaskArtifact
from pipeline.queue.repository import TaskRepository
from datetime import datetime

client = TestClient(app)

@pytest.fixture
def auth_header():
    token = create_access_token({"user_id": "history_user", "role": "external"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_user_header():
    token = create_access_token({"user_id": "other_user", "role": "external"})
    return {"Authorization": f"Bearer {token}"}

def test_get_task_history(auth_header):
    # Setup: Create tasks for history_user
    with get_session() as session:
        repo = TaskRepository(session)
        # Task 1
        t1 = Task(id=101, title="User Task 1", status=TaskStatus.DONE, requester="history_user", created_at=datetime(2026, 3, 20))
        # Task 2
        t2 = Task(id=102, title="User Task 2", status=TaskStatus.FAILED, requester="history_user", created_at=datetime(2026, 3, 21))
        # Task 3 (Other user)
        t3 = Task(id=103, title="Other Task", status=TaskStatus.DONE, requester="other_user", created_at=datetime(2026, 3, 22))

        session.add_all([t1, t2, t3])
        session.commit()

    # Test: Get history for history_user
    response = client.get("/api/tasks/history", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 102  # Descending order by created_at
    assert data[1]["id"] == 101
    assert all(t["requester"] == "history_user" for t in data)

def test_get_task_detail_with_events_and_artifacts(auth_header):
    task_id = 200
    with get_session() as session:
        # Create task
        t = Task(id=task_id, title="Detail Task", status=TaskStatus.DONE, requester="history_user")
        session.add(t)

        # Create events
        e1 = TaskEvent(task_id=task_id, event_type="created", event_metadata='{"init": true}')
        e2 = TaskEvent(task_id=task_id, event_type="started", event_metadata='{"gpu": 0}')
        session.add_all([e1, e2])

        # Create artifacts
        a1 = TaskArtifact(task_id=task_id, format="txt", path="output/200/result.txt")
        a2 = TaskArtifact(task_id=task_id, format="srt", path="output/200/result.srt")
        session.add_all([a1, a2])

        session.commit()

    # Test: Get detail
    response = client.get(f"/api/tasks/{task_id}", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert len(data["events"]) == 2
    assert len(data["artifacts"]) == 2
    assert data["events"][0]["event_type"] == "created"
    assert data["artifacts"][0]["format"] == "txt"

def test_task_access_control(auth_header, other_user_header):
    task_id = 300
    with get_session() as session:
        t = Task(id=task_id, title="Private Task", status=TaskStatus.DONE, requester="history_user")
        session.add(t)
        session.commit()

    # Owner can access
    response = client.get(f"/api/tasks/{task_id}", headers=auth_header)
    assert response.status_code == 200

    # Other user cannot access
    response = client.get(f"/api/tasks/{task_id}", headers=other_user_header)
    assert response.status_code == 404  # Repository.get_task returns None if requester filter fails

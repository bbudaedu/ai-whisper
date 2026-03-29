import pytest
from fastapi import status
from pipeline.queue.models import Task, TaskStatus, TaskSource

def test_patch_task_speaker_name_success(client, auth_header, db_session, user_fixture):
    """測試成功更新 speaker_name。"""
    # 建立一個屬於該使用者的任務
    task = Task(
        title="Test Task",
        video_id="abc12345",
        requester=str(user_fixture.user_id),
        status=TaskStatus.PENDING,
        source=TaskSource.EXTERNAL
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    payload = {"speaker_name": "測試講者"}
    response = client.patch(f"/api/tasks/{task.id}", json=payload, headers=auth_header)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["speaker_name"] == "測試講者"

    # 驗證資料庫是否已更新
    db_session.refresh(task)
    assert task.speaker_name == "測試講者"

def test_patch_task_not_found(client, auth_header):
    """測試更新不存在的任務回傳 404。"""
    payload = {"speaker_name": "測試講者"}
    response = client.patch("/api/tasks/99999", json=payload, headers=auth_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_patch_task_unauthorized(client, db_session, user_fixture):
    """測試未授權（無 Token）回傳 401。"""
    task = Task(
        title="Test Task",
        video_id="abc12345",
        requester=str(user_fixture.user_id),
        status=TaskStatus.PENDING
    )
    db_session.add(task)
    db_session.commit()

    payload = {"speaker_name": "測試講者"}
    response = client.patch(f"/api/tasks/{task.id}", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_patch_task_forbidden(client, auth_header, db_session):
    """測試更新不屬於自己的任務回傳 403。"""
    # 建立一個屬於其他人的任務
    task = Task(
        title="Other's Task",
        video_id="other123",
        requester="other-user-id",
        status=TaskStatus.PENDING,
        source=TaskSource.EXTERNAL
    )
    db_session.add(task)
    db_session.commit()

    payload = {"speaker_name": "測試講者"}
    response = client.patch(f"/api/tasks/{task.id}", json=payload, headers=auth_header)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_task_includes_speaker_name(client, auth_header, db_session, user_fixture):
    """測試 GET /api/tasks/{id} 回傳包含 speaker_name。"""
    task = Task(
        title="Test Task",
        video_id="abc12345",
        requester=str(user_fixture.user_id),
        status=TaskStatus.PENDING,
        speaker_name="原講者"
    )
    db_session.add(task)
    db_session.commit()

    response = client.get(f"/api/tasks/{task.id}", headers=auth_header)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["speaker_name"] == "原講者"

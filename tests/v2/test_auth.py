"""Auth 補缺測試：API Key 交換、Token 過期、RBAC 隔離。"""

from datetime import timedelta

from sqlmodel import Session

from api.auth import create_access_token, hash_token
from api.models import ApiKey


class TestApiKeyExchange:
    """POST /api/auth/token — x-api-key header 交換 JWT。"""

    def test_valid_api_key_returns_tokens(self, client, db_engine):
        """有效的 API Key 應回傳 access_token 和 refresh_token。"""
        raw_key = "test-api-key-12345"
        with Session(db_engine) as session:
            api_key = ApiKey(
                key_hash=hash_token(raw_key),
                user_id="apikey-user-1",
                role="external",
                is_active=True,
            )
            session.add(api_key)
            session.commit()

        response = client.post(
            "/api/auth/token",
            headers={"x-api-key": raw_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_invalid_api_key_returns_401(self, client):
        """無效的 API Key 應回傳 401。"""
        response = client.post(
            "/api/auth/token",
            headers={"x-api-key": "nonexistent-key"},
        )
        assert response.status_code == 401

    def test_missing_api_key_returns_401(self, client):
        """缺少 x-api-key header 應回傳 401。"""
        response = client.post("/api/auth/token")
        assert response.status_code == 401


class TestTokenExpiry:
    """驗證過期 JWT 被拒絕。"""

    def test_expired_token_returns_401(self, client):
        """使用已過期的 JWT 訪問 /api/tasks/history 應回傳 401。"""
        expired_token = create_access_token(
            {"user_id": "test-user", "role": "external"},
            expires_delta=timedelta(seconds=-10),
        )
        response = client.get(
            "/api/tasks/history",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


class TestRoleBasedAccess:
    """驗證 external/internal 角色隔離。"""

    def test_external_cannot_see_others_task(self, client, auth_header, internal_auth_header):
        """external user 查詢他人建立的任務應回 404。"""
        response = client.post(
            "/api/tasks/",
            json={
                "type": "youtube",
                "payload": {
                    "url": "https://www.youtube.com/watch?v=role_test",
                    "title": "Role Test",
                },
            },
            headers=internal_auth_header,
        )
        assert response.status_code == 200
        task_id = response.json()["task_id"]

        response = client.get(f"/api/tasks/{task_id}", headers=auth_header)
        assert response.status_code == 404

    def test_internal_can_see_all_tasks(self, client, auth_header, internal_auth_header):
        """internal user 可以查看所有人的任務。"""
        response = client.post(
            "/api/tasks/",
            json={
                "type": "youtube",
                "payload": {
                    "url": "https://www.youtube.com/watch?v=int_test",
                    "title": "Internal Vis Test",
                },
            },
            headers=auth_header,
        )
        assert response.status_code == 200
        task_id = response.json()["task_id"]

        response = client.get(f"/api/tasks/{task_id}", headers=internal_auth_header)
        assert response.status_code == 200
        assert response.json()["id"] == task_id

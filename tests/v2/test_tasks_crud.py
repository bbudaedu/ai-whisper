"""Tasks CRUD API 測試。"""

import io


class TestCreateTask:
    """POST /api/tasks/ — 建立任務。"""

    def test_create_youtube_task(self, client, auth_header):
        """JSON body type=youtube 應回傳 task_id 與 status=pending。"""
        response = client.post(
            "/api/tasks/",
            json={
                "type": "youtube",
                "payload": {
                    "url": "https://www.youtube.com/watch?v=yt_crud_test",
                    "title": "CRUD 測試影片",
                },
            },
            headers=auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] > 0
        assert data["status"] == "pending"
        assert "created_at" in data

    def test_create_upload_task(self, client, auth_header):
        """multipart upload type=upload 應建立任務並寫入檔案。"""
        import api.routers.tasks as tasks_mod

        wav_content = b"RIFF" + b"\x00" * 100
        response = client.post(
            "/api/tasks/",
            data={"type": "upload", "payload": '{"title": "Upload Test"}'},
            files={"file": ("test.wav", io.BytesIO(wav_content), "audio/wav")},
            headers=auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        task_id = data["task_id"]
        assert task_id > 0

        upload_dir = tasks_mod.OUTPUT_BASE / str(task_id)
        assert upload_dir.exists()
        uploaded_files = list(upload_dir.iterdir())
        assert len(uploaded_files) == 1
        assert uploaded_files[0].name == "test.wav"

    def test_create_task_missing_url_returns_400(self, client, auth_header):
        """YouTube 任務缺少 url 應回 400。"""
        response = client.post(
            "/api/tasks/",
            json={"type": "youtube", "payload": {"title": "No URL"}},
            headers=auth_header,
        )
        assert response.status_code == 400

    def test_create_task_invalid_type_returns_400(self, client, auth_header):
        """無效的 task type 應回 400。"""
        response = client.post(
            "/api/tasks/",
            json={"type": "invalid", "payload": {}},
            headers=auth_header,
        )
        assert response.status_code == 400

    def test_create_task_without_auth_returns_401(self, client):
        """無 token 建立任務應回 401。"""
        response = client.post(
            "/api/tasks/",
            json={"type": "youtube", "payload": {"url": "https://youtu.be/x"}},
        )
        assert response.status_code in (401, 403)


class TestGetTask:
    """GET /api/tasks/{id} 與 GET /api/tasks/history。"""

    def test_get_own_task(self, client, auth_header):
        """external user 可以查看自己建立的任務。"""
        create_resp = client.post(
            "/api/tasks/",
            json={
                "type": "youtube",
                "payload": {"url": "https://youtu.be/own_task", "title": "Own Task"},
            },
            headers=auth_header,
        )
        task_id = create_resp.json()["task_id"]

        response = client.get(f"/api/tasks/{task_id}", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == "Own Task"
        assert data["status"] == "pending"

    def test_get_nonexistent_task_returns_404(self, client, auth_header):
        """查詢不存在的 task_id 應回 404。"""
        response = client.get("/api/tasks/99999", headers=auth_header)
        assert response.status_code == 404

    def test_task_history_returns_list(self, client, auth_header):
        """GET /api/tasks/history 應回傳列表。"""
        for i in range(2):
            client.post(
                "/api/tasks/",
                json={
                    "type": "youtube",
                    "payload": {"url": f"https://youtu.be/hist_{i}", "title": f"History {i}"},
                },
                headers=auth_header,
            )

        response = client.get("/api/tasks/history", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_task_history_pagination(self, client, auth_header):
        """GET /api/tasks/history?page=1&size=1 應只回傳 1 筆。"""
        for i in range(3):
            client.post(
                "/api/tasks/",
                json={
                    "type": "youtube",
                    "payload": {"url": f"https://youtu.be/page_{i}", "title": f"Page {i}"},
                },
                headers=auth_header,
            )

        response = client.get("/api/tasks/history?page=1&size=1", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestCancelTask:
    """POST /api/tasks/{id}/cancel。"""

    def test_cancel_own_task(self, client, auth_header):
        """取消自己的任務應成功。"""
        create_resp = client.post(
            "/api/tasks/",
            json={
                "type": "youtube",
                "payload": {"url": "https://youtu.be/cancel_me", "title": "Cancel Me"},
            },
            headers=auth_header,
        )
        task_id = create_resp.json()["task_id"]

        response = client.post(f"/api/tasks/{task_id}/cancel", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("canceled", "cancelled")

    def test_cancel_others_task_returns_403(self, client, auth_header, internal_auth_header):
        """external user 取消其他人的任務應回 403。"""
        create_resp = client.post(
            "/api/tasks/",
            json={
                "type": "youtube",
                "payload": {"url": "https://youtu.be/not_mine", "title": "Not Mine"},
            },
            headers=internal_auth_header,
        )
        task_id = create_resp.json()["task_id"]

        response = client.post(f"/api/tasks/{task_id}/cancel", headers=auth_header)
        assert response.status_code == 403

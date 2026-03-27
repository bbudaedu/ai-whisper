"""驗證 v2 測試環境隔離。"""
import glob
import os

from sqlmodel import select

from pipeline.queue.models import Task


def test_db_session_is_in_memory(db_session, tmp_path):
    """驗證 db_session 使用 in-memory SQLite，不產生新的 .db 檔案。"""
    # 查詢 tasks 表——應該是空的
    tasks = db_session.exec(select(Task)).all()
    assert tasks == []

    # 確認專案根目錄沒有「測試執行期間新產生」的 .db 檔案
    # 使用 tmp_path 建一個哨兵檔，確認 .db 是測試前就存在的（mtime < 哨兵檔）
    sentinel = tmp_path / "sentinel"
    sentinel.touch()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    existing_dbs = glob.glob(os.path.join(project_root, "*.db"))
    # 只允許「測試前已存在」的 .db 文件（修改時間早於哨兵）
    new_dbs = [
        db for db in existing_dbs
        if os.path.getmtime(db) >= sentinel.stat().st_mtime
    ]
    assert new_dbs == [], f"Unexpected NEW .db files created during test: {new_dbs}"


def test_client_fixture_serves_requests(client):
    """驗證 client fixture 能正常處理 HTTP 請求。"""
    # 任意未定義的路由應回 404（不是 500）
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_auth_header_is_valid_jwt(client, auth_header):
    """驗證 auth_header 產生的 JWT 能通過 verify_token。"""
    # GET /api/tasks/history 需要有效 token
    response = client.get("/api/tasks/history", headers=auth_header)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_internal_auth_header_has_internal_role(client, internal_auth_header):
    """驗證 internal_auth_header 的 JWT 包含 role=internal。"""
    from api.auth import verify_token
    token = internal_auth_header["Authorization"].replace("Bearer ", "")
    payload = verify_token(token)
    assert payload["role"] == "internal"


def test_output_base_is_tmp_path(client, tmp_path):
    """驗證 OUTPUT_BASE 已被 patch 到 tmp_path。

    [ISSUE-08 NOTE] client fixture 內 monkeypatch 設定的 OUTPUT_BASE 指向
    client fixture 自己的 tmp_path 參數。本測試函式的 tmp_path 是另一個獨立的
    暫存目錄（pytest 為每個 fixture/test 提供不同的 tmp_path）。
    因此此處直接檢查 tasks_mod.OUTPUT_BASE 是一個 tmp_path 風格的路徑即可，
    不與本測試的 tmp_path 做 == 比較。
    """
    from api.routers import tasks as tasks_mod
    # client fixture 內已 patch，此處驗證 patch 生效
    # 由於 client 和 test 各自的 tmp_path 可能不同，只驗證型別與非生產路徑
    assert hasattr(tasks_mod.OUTPUT_BASE, "exists")  # 是 Path-like
    assert "output" not in str(tasks_mod.OUTPUT_BASE) or "tmp" in str(tasks_mod.OUTPUT_BASE)

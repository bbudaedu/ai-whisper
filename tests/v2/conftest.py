"""v2 test fixtures — 繼承父層 db_engine/db_session/user_fixture。"""
import sys
import types
from datetime import timedelta

import pytest
from fastapi import FastAPI
from sqlmodel import Session, SQLModel
from starlette.testclient import TestClient

from api.auth import create_access_token


# ── OAuth stub（與 test_external_api_auth.py 相同模式）──
def _install_oauth_stubs():
    """在 import auth router 前安裝 authlib/google stubs。"""
    class FakeOAuth:
        def __init__(self):
            self.google = types.SimpleNamespace(
                authorize_access_token=lambda request: {"id_token": "fake"},
                authorize_redirect=lambda request, callback_url: {"redirect": callback_url},
            )
        def register(self, **kwargs):
            return None

    authlib_module = types.SimpleNamespace(
        integrations=types.SimpleNamespace(
            starlette_client=types.SimpleNamespace(OAuth=FakeOAuth)
        )
    )
    google_auth_module = types.SimpleNamespace(
        transport=types.SimpleNamespace(requests=types.SimpleNamespace(Request=lambda: None))
    )
    google_oauth_module = types.SimpleNamespace(
        id_token=types.SimpleNamespace(verify_oauth2_token=lambda *a, **kw: {})
    )
    sys.modules.setdefault("authlib", authlib_module)
    sys.modules.setdefault("authlib.integrations", authlib_module.integrations)
    sys.modules.setdefault("authlib.integrations.starlette_client", authlib_module.integrations.starlette_client)
    sys.modules.setdefault("google", types.SimpleNamespace(auth=google_auth_module, oauth2=google_oauth_module))
    sys.modules.setdefault("google.auth", google_auth_module)
    sys.modules.setdefault("google.auth.transport", google_auth_module.transport)
    sys.modules.setdefault("google.auth.transport.requests", google_auth_module.transport.requests)
    sys.modules.setdefault("google.oauth2", google_oauth_module)
    sys.modules.setdefault("google.oauth2.id_token", google_oauth_module.id_token)

_install_oauth_stubs()


@pytest.fixture
def client(db_engine, tmp_path, monkeypatch):
    """完整 FastAPI TestClient，包含 auth + tasks + download routers。"""
    # [ISSUE-02 FIX] 確保所有 model 都被 import，
    # 父層 db_engine 只 import Task/StageTask，缺少 TaskEvent/TaskArtifact，
    # 而 tasks router 的 get_task_status 會查詢這兩張表。
    from pipeline.queue.models import Task, StageTask, TaskEvent, TaskArtifact  # noqa: F401
    SQLModel.metadata.create_all(db_engine)

    def _get_session():
        return Session(db_engine)

    # Patch tasks router 依賴
    monkeypatch.setattr("api.routers.tasks.get_session", _get_session)
    monkeypatch.setattr("api.routers.tasks.OUTPUT_BASE", tmp_path)
    monkeypatch.setattr("api.routers.tasks.log_task_event", lambda *a, **kw: None)

    # Patch download router 依賴
    monkeypatch.setattr("api.routers.download.get_session", _get_session)
    monkeypatch.setattr("api.routers.download.OUTPUT_BASE", tmp_path)

    # Patch auth router 依賴
    monkeypatch.setattr("api.routers.auth.get_session", _get_session)

    # Patch pipeline database 依賴
    monkeypatch.setattr("pipeline.queue.database.get_session", _get_session)
    monkeypatch.setattr("pipeline.queue.database.get_engine", lambda: db_engine)

    # Patch JWT secret
    monkeypatch.setenv("JWT_SECRET", "test-secret-v2")
    monkeypatch.setattr("api.auth.JWT_SECRET", "test-secret-v2")

    from api.routers.auth import router as auth_router
    from api.routers.tasks import router as tasks_router
    from api.routers.download import router as download_router

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(tasks_router)
    app.include_router(download_router)

    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def auth_header(user_fixture):
    """產生 external role 的 Bearer Authorization header。"""
    token = create_access_token(
        {"user_id": str(user_fixture.user_id), "role": "external"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def internal_auth_header(db_session):
    """產生 internal role 的 Bearer Authorization header（不需真實 user）。"""
    token = create_access_token(
        {"user_id": "internal-test-user", "role": "internal"}
    )
    return {"Authorization": f"Bearer {token}"}

"""External API auth endpoint tests."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlmodel import Session, SQLModel, select
from starlette.testclient import TestClient

from api.auth import validate_password_strength
from api.models import Identity, User
from api.routers.auth import router as auth_router


@pytest.fixture
def client(db_engine, monkeypatch):
    from api.models import ApiKey, RefreshToken  # noqa: F401
    from pipeline.queue.models import Task, StageTask  # noqa: F401
    SQLModel.metadata.create_all(db_engine)

    def _get_session():
        return Session(db_engine)

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")

    monkeypatch.setattr("api.routers.auth.get_session", _get_session)
    monkeypatch.setattr("pipeline.queue.database.get_session", _get_session)
    monkeypatch.setattr("pipeline.queue.database.get_engine", lambda: db_engine)
    monkeypatch.setattr("pipeline.queue.database.create_db_and_tables", lambda engine=None: None)

    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_success(client, user_fixture):
    response = _login(client, "test@example.com", "StrongPassword123")
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


def test_login_failure(client, user_fixture):
    response = _login(client, "test@example.com", "WrongPassword123")
    assert response.status_code == 401


def test_disabled_user_login(client, disabled_user):
    response = _login(client, "disabled@example.com", "StrongPassword123")
    assert response.status_code == 401


def test_password_strength_validation():
    with pytest.raises(ValueError):
        validate_password_strength("Short1")
    with pytest.raises(ValueError):
        validate_password_strength("lowercaseonly123")
    with pytest.raises(ValueError):
        validate_password_strength("UPPERCASEONLY123")
    with pytest.raises(ValueError):
        validate_password_strength("NoDigitsHere!!")

    validate_password_strength("StrongPassword123")


def test_refresh_token_rotation(client, user_fixture):
    login_response = _login(client, "test@example.com", "StrongPassword123")
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    new_refresh_token = data["refresh_token"]

    reuse_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_response.status_code == 401

    second_refresh = client.post("/api/auth/refresh", json={"refresh_token": new_refresh_token})
    assert second_refresh.status_code == 200


def test_revoke_all_tokens(client, user_fixture):
    first_login = _login(client, "test@example.com", "StrongPassword123")
    second_login = _login(client, "test@example.com", "StrongPassword123")
    assert first_login.status_code == 200
    assert second_login.status_code == 200

    refresh_token_one = first_login.json()["refresh_token"]
    refresh_token_two = second_login.json()["refresh_token"]

    revoke_response = client.post("/api/auth/revoke", json={"refresh_token": refresh_token_one})
    assert revoke_response.status_code == 200

    refresh_one = client.post("/api/auth/refresh", json={"refresh_token": refresh_token_one})
    refresh_two = client.post("/api/auth/refresh", json={"refresh_token": refresh_token_two})
    assert refresh_one.status_code == 401
    assert refresh_two.status_code == 401


def test_google_oauth_callback(client, db_session, db_engine, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"id_token": "fake-id-token"}

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(
        "api.routers.auth.oauth.google.authorize_access_token",
        fake_authorize_access_token,
    )

    existing_user = User(email="existing@example.com", is_active=True, role="external")
    db_session.add(existing_user)
    db_session.commit()
    db_session.refresh(existing_user)

    existing_info = {
        "email": "existing@example.com",
        "sub": "google-sub-123",
        "name": "Existing User",
        "picture": "https://example.com/avatar.png",
    }
    monkeypatch.setattr(
        "api.routers.auth.google_id_token.verify_oauth2_token",
        lambda *args, **kwargs: existing_info,
    )

    response = client.get("/api/auth/google/callback")
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]

    with Session(db_engine) as session:
        identity = session.exec(
            select(Identity).where(
                Identity.provider == "google",
                Identity.provider_id == "google-sub-123",
            )
        ).first()
        assert identity is not None
        assert identity.user_id == existing_user.user_id

    new_info = {
        "email": "new@example.com",
        "sub": "google-sub-456",
        "name": "New User",
        "picture": "https://example.com/avatar2.png",
    }
    monkeypatch.setattr(
        "api.routers.auth.google_id_token.verify_oauth2_token",
        lambda *args, **kwargs: new_info,
    )

    response = client.get("/api/auth/google/callback")
    assert response.status_code == 200

    with Session(db_engine) as session:
        identity = session.exec(
            select(Identity).where(
                Identity.provider == "google",
                Identity.provider_id == "google-sub-456",
            )
        ).first()
        assert identity is not None
        user = session.exec(select(User).where(User.email == "new@example.com")).first()
        assert user is not None
        assert identity.user_id == user.user_id

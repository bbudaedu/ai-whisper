from __future__ import annotations

import os
import secrets

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from api.auth import (
    _config_fallback,
    api_key_header,
    create_access_token,
    hash_token,
    refresh_token_expiry,
)
from api.schemas import LoginRequest, RefreshRequest, RevokeRequest, Token
from pipeline.queue.database import get_session
from pipeline.queue.repository import TaskRepository

router = APIRouter(tags=["Auth"])

# Explicitly exclude register/verify-email/forgot-password/reset-password endpoints.

oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID") or _config_fallback.get("google_client_id"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET")
    or _config_fallback.get("google_client_secret"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.post("/token", response_model=Token)
def exchange_token(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    with get_session() as session:
        repo = TaskRepository(session)
        api_key_record = repo.verify_api_key(api_key)
        if api_key_record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        payload = {"user_id": str(api_key_record.user_id), "role": api_key_record.role}
        access_token = create_access_token(payload)
        refresh_token_raw = secrets.token_urlsafe(48)
        repo.create_refresh_token(
            user_id=str(api_key_record.user_id),
            role=api_key_record.role,
            token_hash=hash_token(refresh_token_raw),
            expires_at=refresh_token_expiry(),
        )
    return Token(access_token=access_token, refresh_token=refresh_token_raw)


@router.post("/login", response_model=Token)
def login(req: LoginRequest):
    with get_session() as session:
        repo = TaskRepository(session)
        user = repo.authenticate_user_by_email(req.email, req.password)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        payload = {"user_id": str(user.user_id), "role": user.role}
        access_token = create_access_token(payload)
        refresh_token_raw = secrets.token_urlsafe(48)
        repo.create_refresh_token(
            user_id=str(user.user_id),
            role=user.role,
            token_hash=hash_token(refresh_token_raw),
            expires_at=refresh_token_expiry(),
        )
    return Token(access_token=access_token, refresh_token=refresh_token_raw)


GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI",
    "https://fayi.budaedu.dpdns.org/api/auth/google/callback",
)


def _process_google_id_token(id_token: str) -> Token:
    client_id = os.environ.get("GOOGLE_CLIENT_ID") or _config_fallback.get("google_client_id")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )
    try:
        id_info = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            audience=client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        ) from exc
    email = id_info.get("email")
    google_sub = id_info.get("sub")
    if not email or not google_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account missing profile",
        )
    name = id_info.get("name") or ""
    avatar_url = id_info.get("picture") or ""
    with get_session() as session:
        repo = TaskRepository(session)
        user = repo.authenticate_google_user(
            email=email,
            google_sub=google_sub,
            name=name,
            avatar_url=avatar_url,
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        payload = {"user_id": str(user.user_id), "role": user.role}
        access_token = create_access_token(payload)
        refresh_token_raw = secrets.token_urlsafe(48)
        repo.create_refresh_token(
            user_id=str(user.user_id),
            role=user.role,
            token_hash=hash_token(refresh_token_raw),
            expires_at=refresh_token_expiry(),
        )
    return Token(access_token=access_token, refresh_token=refresh_token_raw)


@router.api_route("/google/login", methods=["GET", "POST"])
async def google_login(request: Request, redirect_uri: str | None = None):
    if request.method == "POST":
        form_data = await request.form()
        credential = form_data.get("credential")
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Google credential",
            )
        return _process_google_id_token(credential)

    callback_url = redirect_uri or GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, callback_url)


@router.get("/google/callback", response_model=Token, name="google_callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    id_token = token.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Google ID token"
        )
    return _process_google_id_token(id_token)


@router.post("/refresh", response_model=Token)
def refresh_token(req: RefreshRequest):
    refresh_hash = hash_token(req.refresh_token)
    with get_session() as session:
        repo = TaskRepository(session)
        token = repo.verify_and_revoke_refresh_token(refresh_hash)
        if token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        payload = {"user_id": token.user_id, "role": token.role}
        access_token = create_access_token(payload)
        new_refresh_raw = secrets.token_urlsafe(48)
        repo.create_refresh_token(
            user_id=token.user_id,
            role=token.role,
            token_hash=hash_token(new_refresh_raw),
            expires_at=refresh_token_expiry(),
        )
    return Token(access_token=access_token, refresh_token=new_refresh_raw)


@router.post("/revoke")
def revoke_token(req: RevokeRequest):
    refresh_hash = hash_token(req.refresh_token)
    with get_session() as session:
        repo = TaskRepository(session)
        token = repo.verify_and_revoke_refresh_token(refresh_hash)
        if token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        repo.revoke_all_user_refresh_tokens(str(token.user_id))
    return {"status": "revoked"}

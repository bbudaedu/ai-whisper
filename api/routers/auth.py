from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import api_key_header, create_access_token, hash_token, refresh_token_expiry
from api.schemas import LoginRequest, RefreshRequest, RevokeRequest, Token
from pipeline.queue.database import get_session
from pipeline.queue.repository import TaskRepository

router = APIRouter(tags=["Auth"])

# Explicitly exclude register/verify-email/forgot-password/reset-password endpoints.


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

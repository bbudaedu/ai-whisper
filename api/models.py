from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "user"

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    role: str = Field(default="external")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Identity(SQLModel, table=True):
    __tablename__ = "identity"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.user_id", index=True)
    provider: str = Field(index=True)
    provider_id: str
    hashed_password: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    key_hash: str = Field(index=True)
    user_id: str = Field(index=True)
    role: str = Field(default="external", index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True)
    user_id: str = Field(index=True)
    role: str = Field(default="external", index=True)
    is_revoked: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)

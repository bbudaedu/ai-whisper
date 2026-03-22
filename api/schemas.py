from datetime import datetime

from pydantic import BaseModel, EmailStr

from pipeline.queue.models import TaskStatus


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RevokeRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TaskCreateResponse(BaseModel):
    task_id: int
    status: str
    created_at: datetime


class TaskStatusResponse(BaseModel):
    id: int
    title: str
    status: TaskStatus
    created_at: datetime
    requester: str


class TaskCancelResponse(BaseModel):
    status: str
    reason: str

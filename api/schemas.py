from datetime import datetime
from typing import Optional, List

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


class TaskEventSchema(BaseModel):
    id: int
    event_type: str
    event_metadata: Optional[str] = None
    created_at: datetime


class TaskArtifactSchema(BaseModel):
    id: int
    format: str
    path: str
    created_at: datetime


class TaskStatusResponse(BaseModel):
    id: int
    title: str
    status: TaskStatus
    created_at: datetime
    requester: str
    speaker_name: Optional[str] = None
    events: List[TaskEventSchema] = []
    artifacts: List[TaskArtifactSchema] = []


class TaskUpdatePayload(BaseModel):
    speaker_name: Optional[str] = None


class TaskCancelResponse(BaseModel):
    status: str
    reason: str

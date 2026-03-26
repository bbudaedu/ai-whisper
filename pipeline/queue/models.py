import enum
import json
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class TaskSource(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"

class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"

class StageType(str, enum.Enum):
    DOWNLOAD = "download"
    TRANSCRIBE = "transcribe"
    PROOFREAD = "proofread"
    POSTPROCESS = "postprocess"

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    video_id: str = Field(index=True)
    playlist_id: str = Field(default="")
    source: TaskSource = Field(default=TaskSource.INTERNAL)
    requester: Optional[str] = Field(default=None, index=True)
    status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    priority: int = Field(default=0)  # higher = more urgent
    max_retries: int = Field(default=3)
    retry_count: int = Field(default=0)
    error_message: str = Field(default="")
    audio_profile: Optional[str] = Field(default=None)
    source_metadata: Optional[str] = Field(default=None)  # 儲存 JSON string
    parent_task_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

class TaskEvent(SQLModel, table=True):
    __tablename__ = "task_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True, foreign_key="tasks.id")
    event_type: str
    event_metadata: Optional[str] = Field(default=None)  # 儲存 JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskArtifact(SQLModel, table=True):
    __tablename__ = "task_artifacts"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True, foreign_key="tasks.id")
    format: str
    path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StageTask(SQLModel, table=True):
    __tablename__ = "stage_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True, foreign_key="tasks.id")
    stage: StageType
    status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    priority: int = Field(default=0)
    source: TaskSource = Field(default=TaskSource.INTERNAL)
    max_retries: int = Field(default=3)
    retry_count: int = Field(default=0)
    error_message: str = Field(default="")
    output_payload: str = Field(default="")  # JSON string: stage 輸出供下一 stage 使用
    next_retry_at: Optional[datetime] = Field(default=None, index=True)  # 退避排程時間
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    def get_output(self) -> dict:
        """取得 output_payload 解析後的 dict。"""
        if not self.output_payload:
            return {}
        return json.loads(self.output_payload)

    def set_output(self, data: dict) -> None:
        """設定 output_payload（序列化為 JSON）。"""
        self.output_payload = json.dumps(data, ensure_ascii=False)


class PlaylistRecord(SQLModel, table=True):
    __tablename__ = "playlists"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: str = Field(index=True)
    requester: str = Field(index=True)
    enabled: bool = Field(default=True)
    status: str = Field(default="idle")  # idle, running, paused
    total_videos: int = Field(default=0)
    processed_count: int = Field(default=0)
    last_synced_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

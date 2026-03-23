"""Task queue repository — DB 存取與原子操作。"""
import logging
import json
from datetime import datetime
from typing import Optional
import hashlib
import secrets

from api.auth import verify_password
from api.models import ApiKey, RefreshToken, User, Identity

from sqlmodel import Session, select, col
from sqlalchemy import update

from pipeline.queue.models import (
    Task,
    StageTask,
    TaskEvent,
    TaskArtifact,
    TaskStatus,
    TaskSource,
    StageType,
)

logger = logging.getLogger(__name__)


class TaskRepository:
    """任務佇列的 DB 存取層。"""

    def __init__(self, session: Session):
        self.session = session

    # ── 任務建立 ──────────────────────────────────

    def create_task(
        self,
        title: str,
        video_id: str,
        playlist_id: str = "",
        source: TaskSource = TaskSource.INTERNAL,
        parent_task_id: Optional[int] = None,
        max_retries: int = 3,
    ) -> Task:
        """建立新任務（pending 狀態）。"""
        priority = 10 if source == TaskSource.INTERNAL else 0
        task = Task(
            title=title,
            video_id=video_id,
            playlist_id=playlist_id,
            source=source,
            status=TaskStatus.PENDING,
            priority=priority,
            max_retries=max_retries,
            parent_task_id=parent_task_id,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def create_playlist_parent_task(
        self,
        playlist_id: str,
        playlist_title: str,
        source: TaskSource = TaskSource.INTERNAL,
    ) -> Task:
        """建立播放清單父任務。

        父任務本身不執行 stage，而是作為子任務的容器。
        子任務（每集影片）透過 parent_task_id 關聯。
        """
        return self.create_task(
            title=playlist_title,
            video_id="",
            playlist_id=playlist_id,
            source=source,
            parent_task_id=None,
        )

    def create_child_task(
        self,
        parent_task_id: int,
        title: str,
        video_id: str,
        playlist_id: str = "",
        source: TaskSource = TaskSource.INTERNAL,
        max_retries: int = 3,
    ) -> Task:
        """建立子任務（關聯到父任務）。"""
        return self.create_task(
            title=title,
            video_id=video_id,
            playlist_id=playlist_id,
            source=source,
            parent_task_id=parent_task_id,
            max_retries=max_retries,
        )

    def create_stage_task(
        self,
        task_id: int,
        stage: StageType,
        source: TaskSource = TaskSource.INTERNAL,
        priority: int = 0,
        max_retries: int = 3,
    ) -> StageTask:
        """為指定 task 建立 stage 子任務。"""
        if source == TaskSource.INTERNAL:
            priority = max(priority, 10)
        stage_task = StageTask(
            task_id=task_id,
            stage=stage,
            status=TaskStatus.PENDING,
            source=source,
            priority=priority,
            max_retries=max_retries,
        )
        self.session.add(stage_task)
        self.session.commit()
        self.session.refresh(stage_task)
        return stage_task

    # ── 原子 Claim ──────────────────────────────────

    def claim_next_stage(
        self,
        stage_filter: Optional[StageType] = None,
    ) -> Optional[StageTask]:
        """原子地 claim 下一個可執行的 stage task。

        排序邏輯：
        1. source=internal (priority DESC) 優先
        2. 同 source 內按 created_at ASC
        3. 可選擇性過濾特定 stage type
        4. 排除 next_retry_at 未到時間的任務（退避中）
        """
        now = datetime.utcnow()
        query = (
            select(StageTask)
            .where(StageTask.status == TaskStatus.PENDING)
            .where(
                (StageTask.next_retry_at == None) | (StageTask.next_retry_at <= now)  # noqa: E711
            )
        )
        if stage_filter is not None:
            query = query.where(StageTask.stage == stage_filter)

        query = query.order_by(
            col(StageTask.priority).desc(),
            col(StageTask.created_at).asc(),
        ).limit(1)

        stage_task = self.session.exec(query).first()
        if stage_task is None:
            return None

        stmt = (
            update(StageTask)
            .where(StageTask.id == stage_task.id)
            .where(StageTask.status == TaskStatus.PENDING)
            .values(status=TaskStatus.RUNNING, started_at=now, updated_at=now)
        )
        result = self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

        if result.rowcount == 0:  # type: ignore[union-attr]
            return None

        self.session.refresh(stage_task)
        return stage_task

    # ── Stage 輸出儲存 ──────────────────────────────────

    def save_stage_output(self, stage_task_id: int, output: dict) -> None:
        """儲存 stage 的執行結果至 output_payload。"""
        stage = self.session.get(StageTask, stage_task_id)
        if stage is None:
            return
        stage.set_output(output)
        stage.updated_at = datetime.utcnow()
        self.session.commit()

    def get_previous_stage_output(self, task_id: int, stage: StageType) -> dict:
        """取得同一 task 的前一 stage 的輸出。"""
        from pipeline.queue.stage_runner import STAGE_ORDER

        stage_idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else -1
        if stage_idx <= 0:
            return {}

        prev_stage_type = STAGE_ORDER[stage_idx - 1]
        query = (
            select(StageTask)
            .where(StageTask.task_id == task_id)
            .where(StageTask.stage == prev_stage_type)
            .where(StageTask.status == TaskStatus.DONE)
            .order_by(col(StageTask.completed_at).desc())
            .limit(1)
        )
        prev = self.session.exec(query).first()
        if prev is None:
            return {}
        return prev.get_output()

    # ── 狀態更新 ──────────────────────────────────

    def complete_stage(self, stage_task_id: int) -> None:
        """標記 stage 為 done。"""
        now = datetime.utcnow()
        stmt = (
            update(StageTask)
            .where(StageTask.id == stage_task_id)
            .values(status=TaskStatus.DONE, completed_at=now, updated_at=now)
        )
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

    def fail_stage(self, stage_task_id: int, error_message: str) -> None:
        """標記 stage 為 failed，記錄錯誤訊息。"""
        now = datetime.utcnow()
        stmt = (
            update(StageTask)
            .where(StageTask.id == stage_task_id)
            .values(
                status=TaskStatus.FAILED,
                error_message=error_message,
                completed_at=now,
                updated_at=now,
            )
        )
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

    def mark_stage_for_retry(
        self, stage_task_id: int, error_message: str, backoff_seconds: float = 0
    ) -> bool:
        """嘗試重試 stage：增加 retry_count，設定 next_retry_at。"""
        from datetime import timedelta

        stage = self.session.get(StageTask, stage_task_id)
        if stage is None:
            return False

        stage.retry_count += 1
        stage.error_message = error_message
        stage.updated_at = datetime.utcnow()

        if stage.retry_count >= stage.max_retries:
            stage.status = TaskStatus.FAILED
            stage.completed_at = datetime.utcnow()
            self.session.commit()
            return False

        stage.status = TaskStatus.PENDING
        stage.started_at = None
        if backoff_seconds > 0:
            stage.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
        else:
            stage.next_retry_at = None
        self.session.commit()
        return True

    # ── 父任務狀態 ──────────────────────────────────

    def check_and_update_parent_status(self, parent_task_id: int) -> None:
        """檢查父任務的所有子任務，更新父任務狀態。"""
        children = self.get_child_tasks(parent_task_id)
        if not children:
            return

        statuses = {c.status for c in children}
        if statuses == {TaskStatus.DONE}:
            self.update_task_status(parent_task_id, TaskStatus.DONE)
        elif TaskStatus.FAILED in statuses and TaskStatus.PENDING not in statuses and TaskStatus.RUNNING not in statuses:
            self.update_task_status(parent_task_id, TaskStatus.FAILED)
        elif TaskStatus.RUNNING in statuses or TaskStatus.PENDING in statuses:
            self.update_task_status(parent_task_id, TaskStatus.RUNNING)

    # ── 查詢 ──────────────────────────────────

    def get_running_stages(
        self,
        stage_filter: Optional[StageType] = None,
    ) -> list[StageTask]:
        """查詢目前 running 的 stage tasks。"""
        query = select(StageTask).where(StageTask.status == TaskStatus.RUNNING)
        if stage_filter is not None:
            query = query.where(StageTask.stage == stage_filter)
        return list(self.session.exec(query).all())

    def get_task(self, task_id: int, requester: Optional[str] = None) -> Optional[Task]:
        """根據 ID 取得 Task，可選擇限制 requester。"""
        task = self.session.get(Task, task_id)
        if task is None:
            return None
        if requester and task.requester != requester:
            return None
        return task

    def get_tasks(
        self,
        requester: Optional[str] = None,
        status: Optional[TaskStatus] = None,
    ) -> list[Task]:
        """查詢任務清單，可選擇限制 requester 與狀態。"""
        query = select(Task)
        if requester:
            query = query.where(Task.requester == requester)
        if status is not None:
            query = query.where(Task.status == status)
        query = query.order_by(col(Task.created_at).desc())
        return list(self.session.exec(query).all())

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """根據 ID 取得 Task。"""
        return self.session.get(Task, task_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """透過 email 查詢使用者。"""
        query = select(User).where(User.email == email).limit(1)
        return self.session.exec(query).first()

    def create_user_with_password(
        self,
        email: str,
        name: str,
        hashed_password: str,
        role: str = "external",
    ) -> User:
        """建立使用者並綁定 email/password Identity。"""
        user = User(email=email, name=name, role=role)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        identity = Identity(
            user_id=user.user_id,
            provider="email",
            provider_id=email,
            hashed_password=hashed_password,
        )
        self.session.add(identity)
        self.session.commit()
        return user

    def authenticate_user_by_email(self, email: str, password: str) -> Optional[User]:
        """驗證 email/password，回傳 User 或 None。"""
        query = (
            select(User, Identity)
            .where(User.email == email)
            .where(Identity.user_id == User.user_id)
            .where(Identity.provider == "email")
            .where(Identity.provider_id == email)
        )
        identity_row = self.session.exec(query).first()
        if identity_row is None:
            return None
        user, identity = identity_row
        if not user.is_active:
            return None
        if not identity.hashed_password:
            return None
        if not verify_password(password, identity.hashed_password):
            return None
        return user

    def authenticate_google_user(
        self,
        email: str,
        google_sub: str,
        name: str,
        avatar_url: str,
    ) -> Optional[User]:
        """驗證 Google OAuth，綁定或建立使用者並同步基本資料。"""
        identity_query = (
            select(Identity)
            .where(Identity.provider == "google")
            .where(Identity.provider_id == google_sub)
            .limit(1)
        )
        identity = self.session.exec(identity_query).first()
        if identity is not None:
            user = self.session.get(User, identity.user_id)
            if user is None:
                return None
            if name:
                user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            user.updated_at = datetime.utcnow()
            self.session.add(user)
            self.session.commit()
            if not user.is_active:
                return None
            return user

        user = self.get_user_by_email(email)
        if user is None:
            user = User(email=email, name=name, avatar_url=avatar_url, role="external")
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
        else:
            if name:
                user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            user.updated_at = datetime.utcnow()
            self.session.add(user)
            self.session.commit()

        identity = Identity(
            user_id=user.user_id,
            provider="google",
            provider_id=google_sub,
        )
        self.session.add(identity)
        self.session.commit()

        if not user.is_active:
            return None
        return user

    def get_task_by_video_id(self, video_id: str) -> Optional[Task]:
        """根據 video_id 查詢任務（用於 fallback 查詢）。"""
        query = select(Task).where(Task.video_id == video_id).limit(1)
        return self.session.exec(query).first()

    def get_child_tasks(self, parent_task_id: int) -> list[Task]:
        """取得父任務的所有子任務。"""
        query = (
            select(Task)
            .where(Task.parent_task_id == parent_task_id)
            .order_by(col(Task.created_at).asc())
        )
        return list(self.session.exec(query).all())

    def get_stages_for_task(self, task_id: int) -> list[StageTask]:
        """取得某 Task 的所有 stage tasks。"""
        query = (
            select(StageTask)
            .where(StageTask.task_id == task_id)
            .order_by(col(StageTask.created_at).asc())
        )
        return list(self.session.exec(query).all())

    # ── 事件與產出 ──────────────────────────────────

    def add_event(self, task_id: int, event_type: str, metadata: dict = None) -> TaskEvent:
        """新增任務事件。"""
        metadata_str = json.dumps(metadata, ensure_ascii=False) if metadata else None
        event = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            event_metadata=metadata_str,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def add_artifact(self, task_id: int, format: str, path: str) -> TaskArtifact:
        """新增任務產出檔案紀錄。"""
        artifact = TaskArtifact(
            task_id=task_id,
            format=format,
            path=path,
        )
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def get_events(self, task_id: int) -> list[TaskEvent]:
        """取得任務的所有事件。"""
        query = (
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(col(TaskEvent.created_at).asc())
        )
        return list(self.session.exec(query).all())

    def get_artifacts(self, task_id: int) -> list[TaskArtifact]:
        """取得任務的所有產出檔案。"""
        query = (
            select(TaskArtifact)
            .where(TaskArtifact.task_id == task_id)
            .order_by(col(TaskArtifact.created_at).asc())
        )
        return list(self.session.exec(query).all())

    def count_pending_stages(self) -> int:
        """計算 pending stage 數量。"""
        query = select(StageTask).where(StageTask.status == TaskStatus.PENDING)
        return len(list(self.session.exec(query).all()))

    def update_task_status(self, task_id: int, status: TaskStatus) -> None:
        """更新 Task 的整體狀態。"""
        now = datetime.utcnow()
        values: dict = {"status": status, "updated_at": now}
        if status in (TaskStatus.DONE, TaskStatus.FAILED):
            values["completed_at"] = now
        stmt = update(Task).where(Task.id == task_id).values(**values)
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

    def cancel_task(self, task_id: int, requester: str, role: str) -> dict:
        """取消指定 task，回傳狀態與原因。"""
        task = self.session.get(Task, task_id)
        if task is None:
            return {"status": "not_found", "reason": "task_not_found"}
        if role != "internal" and task.requester != requester:
            return {"status": "error", "reason": "unauthorized"}
        if task.status not in {TaskStatus.PENDING, TaskStatus.QUEUED}:
            return {"status": "unchanged", "reason": "task_already_running"}

        task.status = TaskStatus.CANCELED
        task.error_message = "client_cancel"
        task.updated_at = datetime.utcnow()
        self.session.add(task)

        stages = self.get_stages_for_task(task_id)
        for stage in stages:
            if stage.status in {TaskStatus.PENDING, TaskStatus.QUEUED}:
                stage.status = TaskStatus.CANCELED
                stage.error_message = "client_cancel"
                stage.updated_at = datetime.utcnow()
                self.session.add(stage)

        self.session.commit()
        return {"status": "canceled", "reason": "client_cancel"}

    # ── API Keys ──────────────────────────────────

    def create_api_key(self, user_id: str, role: str) -> str:
        """建立新的 API key，回傳 raw key（僅顯示一次）。"""
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        api_key = ApiKey(
            key_hash=key_hash,
            user_id=user_id,
            role=role,
            is_active=True,
        )
        self.session.add(api_key)
        self.session.commit()
        return raw_key

    def revoke_api_key(self, user_id: str) -> None:
        """撤銷指定 user 的 API key。"""
        stmt = update(ApiKey).where(ApiKey.user_id == user_id).values(is_active=False)
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

    def verify_api_key(self, raw_key: str) -> Optional[ApiKey]:
        """驗證 raw key，回傳 ApiKey（若有效）。"""
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        query = (
            select(ApiKey)
            .where(ApiKey.key_hash == key_hash)
            .where(ApiKey.is_active == True)  # noqa: E712
            .limit(1)
        )
        return self.session.exec(query).first()

    # ── Refresh Tokens ──────────────────────────────────

    def create_refresh_token(
        self, user_id: str, role: str, token_hash: str, expires_at: datetime
    ) -> None:
        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user_id,
            role=role,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.session.add(refresh_token)
        self.session.commit()

    def verify_and_revoke_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        now = datetime.utcnow()
        query = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.is_revoked == False)  # noqa: E712
            .where((RefreshToken.expires_at == None) | (RefreshToken.expires_at > now))  # noqa: E711
            .limit(1)
        )
        token = self.session.exec(query).first()
        if token is None:
            return None
        token.is_revoked = True
        self.session.add(token)
        self.session.commit()
        return token

    def revoke_refresh_token(self, token_hash: str) -> None:
        stmt = update(RefreshToken).where(RefreshToken.token_hash == token_hash).values(is_revoked=True)
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

    def revoke_all_user_refresh_tokens(self, user_id: str) -> None:
        stmt = update(RefreshToken).where(RefreshToken.user_id == user_id).values(is_revoked=True)
        self.session.exec(stmt)  # type: ignore[arg-type]
        self.session.commit()

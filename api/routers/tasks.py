import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import verify_token
from api.schemas import TaskCreateResponse
from pipeline.queue.database import get_session
from pipeline.queue.models import TaskSource, TaskStatus
from pipeline.queue.repository import TaskRepository
from pipeline.queue.stage_runner import create_initial_stages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

http_bearer = HTTPBearer(auto_error=False)


def _parse_output_formats(raw: Any) -> list[str]:
    if raw is None:
        return ["srt", "vtt", "txt"]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return ["srt", "vtt", "txt"]
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in text.split(",") if item.strip()]
    return [str(raw).strip()] if str(raw).strip() else ["srt", "vtt", "txt"]


def _parse_payload(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"prompt": text}
        return {}
    return {"value": raw}


def _resolve_requester(payload: dict, requester: str | None) -> str:
    if requester:
        return requester
    payload_requester = payload.get("requester")
    if isinstance(payload_requester, str) and payload_requester.strip():
        return payload_requester.strip()
    return ""


def _parse_youtube_video_id(url: str) -> str:
    if not url:
        return ""
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    return url


def _get_task_source(source: str | None) -> TaskSource:
    if source == "internal":
        return TaskSource.INTERNAL
    return TaskSource.EXTERNAL


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return verify_token(credentials.credentials)


@router.post("/", response_model=TaskCreateResponse)
async def create_task(request: Request, user: dict = Depends(get_current_user)):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        payload = _parse_payload(body.get("payload"))
        task_type = body.get("type")
        source = body.get("source")
        output_formats = _parse_output_formats(body.get("output_formats"))
        file = None
    elif "multipart/form-data" in content_type:
        form = await request.form()
        task_type = form.get("type")
        source = form.get("source")
        payload = _parse_payload(form.get("payload"))
        output_formats = _parse_output_formats(form.get("output_formats"))
        file = form.get("file")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported content type")

    if task_type not in {"upload", "youtube"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task type")

    requester = _resolve_requester(payload, user.get("user_id"))
    if not requester:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requester required")

    if task_type == "upload":
        if not isinstance(file, UploadFile):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File required for upload")
        video_id = payload.get("video_id") or file.filename or ""
        title = payload.get("title") or file.filename or "upload"
        playlist_id = payload.get("playlist_id", "")
    else:
        url = payload.get("url")
        if not url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing youtube url")
        video_id = _parse_youtube_video_id(url)
        title = payload.get("title") or video_id or "youtube"
        playlist_id = payload.get("playlist_id", "")

    if not video_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing video id")

    with get_session() as session:
        repo = TaskRepository(session)
        task = repo.create_task(
            title=title,
            video_id=video_id,
            playlist_id=playlist_id,
            source=_get_task_source(source),
        )
        task.requester = requester
        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)
        create_initial_stages(session, task)

    logger.info(
        "Task created via API: id=%s type=%s requester=%s formats=%s",
        task.id,
        task_type,
        requester,
        output_formats,
    )

    return TaskCreateResponse(
        task_id=task.id,
        status=task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
        created_at=task.created_at,
    )

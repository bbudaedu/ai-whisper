from __future__ import annotations

import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import verify_token
from pipeline.queue.database import get_session
from pipeline.queue.models import TaskStatus
from pipeline.queue.repository import TaskRepository

router = APIRouter(prefix="/api/tasks", tags=["Download"])
http_bearer = HTTPBearer(auto_error=False)

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_BASE = BASE_DIR / "output"
ALLOWED_SUFFIXES = {".srt", ".txt", ".xlsx", ".docx", ".vtt", ".json", ".tsv"}


def _collect_output_files(output_dir: Path) -> list[Path]:
    if not output_dir.exists() or not output_dir.is_dir():
        return []
    files: list[Path] = []
    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES:
            files.append(path)
    return files


from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query, Request

# ...

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> dict:
    auth_token = None
    if credentials and credentials.credentials:
        auth_token = credentials.credentials
    else:
        # 手動從 Query Parameter 讀取 token
        auth_token = request.query_params.get("token")

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return verify_token(auth_token)


@router.get("/{task_id}/download")
async def download_task_results(
    task_id: int,
    background_tasks: BackgroundTasks,
    format: str | None = Query(default=None, description="Optional format filter: txt,srt,vtt,json,tsv,docx,xlsx"),
    user: dict = Depends(get_current_user),
):
    requester = user.get("user_id") or ""
    role = user.get("role") or "external"

    with get_session() as session:
        repo = TaskRepository(session)
        task = repo.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if role != "internal" and task.requester != requester:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if task.status != TaskStatus.DONE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task not completed")

    print(f"DEBUG: Downloading task {task_id}, status={task.status}, requester={task.requester}")
    print(f"DEBUG: OUTPUT_BASE={OUTPUT_BASE}, exists={OUTPUT_BASE.exists()}")

    output_dirs: list[Path] = []
    if task.video_id:
        output_dirs.append(OUTPUT_BASE / str(task.video_id))
    output_dirs.append(OUTPUT_BASE / str(task.id))

    print(f"DEBUG: Candidates: {[str(d) for d in output_dirs]}")

    files: list[Path] = []
    selected_dir: Path | None = None
    for candidate in output_dirs:
        print(f"DEBUG: Checking candidate {candidate}, exists={candidate.exists()}")
        files = _collect_output_files(candidate)
        print(f"DEBUG: Found {len(files)} files in {candidate}")
        if files:
            selected_dir = candidate
            break

    if not files or selected_dir is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output files not found")

    if format:
        normalized = format.lower().lstrip('.')
        # Support aliases for word/excel
        format_map = {
            "word": ".docx",
            "excel": ".xlsx",
            "docx": ".docx",
            "xlsx": ".xlsx",
            "txt": ".txt",
            "srt": ".srt",
            "vtt": ".vtt",
            "json": ".json",
            "tsv": ".tsv",
        }
        requested_suffix = format_map.get(normalized, f".{normalized}")

        if requested_suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported format")

        files = [path for path in files if path.suffix.lower() == requested_suffix]
        if not files:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested format not found")

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    zip_name = f"{task.id}_{timestamp}.zip"

    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip.close()

    with zipfile.ZipFile(temp_zip.name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            arcname = file_path.relative_to(selected_dir)
            zf.write(file_path, arcname.as_posix())

    background_tasks.add_task(os.remove, temp_zip.name)

    return FileResponse(
        path=temp_zip.name,
        filename=zip_name,
        media_type="application/zip",
    )

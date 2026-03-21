import asyncio
import json
import os
import subprocess
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from api.auth import create_access_token, hash_token, refresh_token_expiry
from api.schemas import Token, RefreshRequest, RevokeRequest
from api.routers.download import router as download_router
from api.routers.tasks import router as tasks_router
from pipeline.queue.database import create_db_and_tables, get_session
from pipeline.queue.models import TaskSource, StageType
from pipeline.queue.repository import TaskRepository
from pipeline.queue.scheduler import TaskScheduler
from pipeline.queue.stage_runner import create_initial_stages
from pipeline.playlist_manager import PlaylistManager
from pipeline.notebooklm_client import NotebookLMClient
from pipeline.notebooklm_scheduler import NotebookLMScheduler
from gpu_lock import is_gpu_busy

# --- Task Queue Scheduler ---
_scheduler: TaskScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: 啟動排程器 + DB 初始化。"""
    global _scheduler

    # Startup: 初始化 DB 並啟動排程器
    create_db_and_tables()

    _scheduler = TaskScheduler(
        session_factory=get_session,
        stage_executors=TaskScheduler.build_default_executors(),
        poll_interval=5,
    )
    await _scheduler.start()

    yield

    # Shutdown: 停止排程器
    if _scheduler is not None:
        await _scheduler.stop()
        _scheduler = None

app = FastAPI(lifespan=lifespan)

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(download_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
  "playlist_url": "https://www.youtube.com/playlist?list=PLpyk9ZaUyAgGLftJLKQQefuK0bDV3iV73",
  "nas_output_base": "/mnt/nas/Whisper_auto_rum/T097V",
  "api_base_url": "http://192.168.100.201:8045/v1/chat/completions",
  "api_key": "sk-8f3999c2452d4124835ffaff469e22af",
  "proofread_model": "gemini-3-flash",
  "proofread_chunk_size": 100,
  "lecture_pdf": "/mnt/nas/Whisper_auto_rum/T097V/CH857-03-01-001.pdf",
  "whisper_model": "large-v2",
  "whisper_lang": "Chinese",
  "whisper_prompt": "佛教公案選集 不要標點符號 ",
  "email_to": "jackyfang@budaedu.org, tyguo@budaedu.org, zrwang@budaedu.org",
  "punct_chunk_size": 120
}

@app.get("/api/config")
def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
            except Exception:
                pass
    return DEFAULT_CONFIG

@app.get("/api/default-proofread-prompt")
def get_default_proofread_prompt():
    prompt_path = os.path.join(BASE_DIR, "skills", "buddhist-proofreading", "prompts", "proofread.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return {"prompt": f.read()}
    return {"prompt": ""}

@app.post("/api/config")
async def save_config(req: Request):
    data = await req.json()

    existing = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except Exception:
                pass

    new_config = {**existing, **data}

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, ensure_ascii=False, indent=2)
    return {"status": "success"}


@app.post("/api/auth/token", response_model=Token)
def exchange_token(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    with get_session() as session:
        repo = TaskRepository(session)
        api_key_record = repo.verify_api_key(api_key)
        if api_key_record is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        payload = {"user_id": api_key_record.user_id, "role": api_key_record.role}
        access_token = create_access_token(payload)
        refresh_token_raw = secrets.token_urlsafe(48)
        refresh_hash = hash_token(refresh_token_raw)
        repo.create_refresh_token(
            user_id=api_key_record.user_id,
            role=api_key_record.role,
            token_hash=refresh_hash,
            expires_at=refresh_token_expiry(),
        )
    return Token(access_token=access_token, refresh_token=refresh_token_raw)


@app.post("/api/auth/refresh", response_model=Token)
def refresh_token(req: RefreshRequest):
    refresh_hash = hash_token(req.refresh_token)
    with get_session() as session:
        repo = TaskRepository(session)
        token = repo.verify_and_revoke_refresh_token(refresh_hash)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
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


@app.post("/api/auth/revoke")
def revoke_token(req: RevokeRequest):
    refresh_hash = hash_token(req.refresh_token)
    with get_session() as session:
        repo = TaskRepository(session)
        repo.revoke_refresh_token(refresh_hash)
    return {"status": "revoked"}

# --- Playlist Management API ---
playlist_manager = PlaylistManager(config_file=CONFIG_FILE)

class PlaylistReq(BaseModel):
    id: str
    name: str
    url: str
    output_dir: str
    whisper_model: str = "large-v3"
    enabled: bool = True
    schedule: str = "daily"
    whisper_lang: str = "auto"
    whisper_prompt: str = "繁體中文"
    proofread_prompt: str = ""
    lecture_pdf: str = ""
    batch_size: int = 5
    folder_prefix: str = "T097V"

@app.get("/api/playlists")
def get_playlists():
    # Reload config to ensure we have the latest
    playlist_manager._config = playlist_manager._load_config()
    return playlist_manager.playlists

@app.post("/api/playlists")
def create_playlist(req: PlaylistReq):
    try:
        playlist_manager.add_playlist(
            playlist_id=req.id,
            name=req.name,
            url=req.url,
            output_dir=req.output_dir,
            whisper_model=req.whisper_model,
            enabled=req.enabled,
            schedule=req.schedule,
            whisper_lang=req.whisper_lang,
            whisper_prompt=req.whisper_prompt,
            proofread_prompt=req.proofread_prompt,
            lecture_pdf=req.lecture_pdf,
            batch_size=req.batch_size,
            folder_prefix=req.folder_prefix,
        )
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/playlists/{playlist_id}")
async def update_playlist_endpoint(playlist_id: str, req: Request):
    """PATCH-style 更新清單欄位。"""
    playlist_manager._config = playlist_manager._load_config()
    if not playlist_manager.get_playlist_by_id(playlist_id):
        raise HTTPException(status_code=404, detail="Playlist not found")
    data = await req.json()
    playlist_manager.update_playlist(playlist_id, data)
    return {"status": "success"}

@app.delete("/api/playlists/{playlist_id}")
def delete_playlist(playlist_id: str):
    playlist_manager.remove_playlist(playlist_id)
    return {"status": "success"}


class ControlReq(BaseModel):
    action: str  # start | pause | resume

@app.post("/api/playlists/{playlist_id}/control")
def control_playlist(playlist_id: str, req: ControlReq):
    """控制單一清單的處理狀態。"""
    playlist_manager._config = playlist_manager._load_config()
    playlist = playlist_manager.get_playlist_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    action_map = {
        "start": "running",
        "pause": "paused",
        "resume": "running",
    }
    new_status = action_map.get(req.action)
    if not new_status:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    playlist_manager.set_status(playlist_id, new_status)
    return {"status": "success", "new_status": new_status}

@app.get("/api/playlists/{playlist_id}/episodes")
def get_playlist_episodes(playlist_id: str):
    """
    獲取特定 playlist 的所有處理過的 episodes (與其詳細的實體檔案狀態)。
    如果是 __legacy__，則拉出無 playlist_id 的清單。
    """
    playlist_manager._config = playlist_manager._load_config()
    playlist = None

    if playlist_id != "__legacy__":
        playlist = playlist_manager.get_playlist_by_id(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

    json_path = os.path.join(BASE_DIR, "processed_videos.json")
    processed = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                processed = json.load(f)
        except Exception:
            pass

    nas_output_base = playlist_manager._config.get("nas_output_base", "/mnt/nas/Whisper_auto_rum")
    if playlist:
        prefix = playlist.get("folder_prefix", "T097V")
        target_dir = os.path.join(nas_output_base, prefix)
    else:
        # For legacy fallback
        prefix = "T097V"
        target_dir = os.path.join(nas_output_base, prefix)

    import re, glob
    episodes = []
    
    for vid, info in processed.items():
        # Correctly bucket episodes:
        # 1. If looking for __legacy__, include videos with no playlist_id OR playlist_id == "__legacy__"
        # 2. If looking for a specific ID, match exactly.
        info_pl_id = info.get("playlist_id")
        if playlist_id == "__legacy__":
            if info_pl_id and info_pl_id != "__legacy__":
                continue
        else:
            if info_pl_id != playlist_id:
                continue
            
        title = info.get("title", "")
        match = re.search(r'(\d+)\s*$', title)
        
        # 狀態追蹤
        status = {
            "video_id": vid,
            "title": title,
            "download_done": False,
            "whisper_done": False,
            "proofread_done": False,
            "report_done": False,
            "error": False
        }
        
        if match:
            ep = str(int(match.group(1))).zfill(3)
            ep_dir = os.path.join(target_dir, f"{prefix}{ep}")
            
            if os.path.isdir(ep_dir):
                # Check download (wav or mp4)
                if glob.glob(os.path.join(ep_dir, "*.wav")) or glob.glob(os.path.join(ep_dir, "*.mp4")):
                    status["download_done"] = True
                
                # Check whisper
                if glob.glob(os.path.join(ep_dir, "*.srt")) and glob.glob(os.path.join(ep_dir, "*.txt")):
                    status["whisper_done"] = True
                    
                # Check proofread
                if glob.glob(os.path.join(ep_dir, "*_proofread.srt")):
                    status["proofread_done"] = True
                    
                # Check reports
                if glob.glob(os.path.join(ep_dir, "*.xlsx")) and glob.glob(os.path.join(ep_dir, "*.docx")):
                    status["report_done"] = True
        
        episodes.append(status)
        
    return {"episodes": episodes}

@app.post("/api/playlists/{playlist_id}/episodes/{video_id}/redo")
async def redo_episode(playlist_id: str, video_id: str, req: Request):
    """
    重做特定影片或特定步驟。
    target_step: 'download', 'transcribe', 'proofread', 'report'
    """
    data = await req.json()
    target_step = data.get("target_step")  # download, transcribe, proofread, report

    playlist_manager._config = playlist_manager._load_config()
    playlist = playlist_manager.get_playlist_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    json_path = os.path.join(BASE_DIR, "processed_videos.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="processed_videos.json not found")

    with open(json_path, "r", encoding="utf-8") as f:
        processed = json.load(f)

    if video_id not in processed:
        raise HTTPException(status_code=404, detail="Video ID not found in processed records")
        
    info = processed[video_id]
    if playlist_id == "__legacy__":
        if info.get("playlist_id"):
            raise HTTPException(status_code=400, detail="Video does not belong to __legacy__")
    else:
        if info.get("playlist_id") != playlist_id:
            raise HTTPException(status_code=400, detail="Video does not belong to this playlist")

    title = info.get("title", "")
    import re, shutil, glob
    match = re.search(r'(\d+)\s*$', title)
    
    if not match:
         raise HTTPException(status_code=400, detail="Could not determine episode number from title")

    nas_output_base = playlist_manager._config.get("nas_output_base", "/mnt/nas/Whisper_auto_rum/T097V")
    if playlist:
        base_config_output_dir = playlist.get("output_dir", "")
        if base_config_output_dir:
            target_dir = os.path.join(nas_output_base, base_config_output_dir)
        else:
            target_dir = nas_output_base
        prefix = playlist.get("folder_prefix", "T097V")
    else:
        # Legacy fallback
        target_dir = os.path.join(nas_output_base, "T097V")
        prefix = "T097V"

    ep = str(int(match.group(1))).zfill(3)
    ep_dir = os.path.join(target_dir, f"{prefix}{ep}")

    if not os.path.isdir(ep_dir):
        # Even if dir is gone, we might still want to clean JSON if step is download
        if target_step and target_step != "download":
             raise HTTPException(status_code=404, detail=f"Episode directory not found: {ep_dir}")

    message = ""
    # 執行刪除邏輯
    try:
        if not target_step or target_step == "download":
            # 完整重做: 刪除整個資料夾 + 從 JSON 移除
            if os.path.isdir(ep_dir):
                shutil.rmtree(ep_dir)
            if video_id in processed:
                del processed[video_id]
            message = f"Video {video_id} completely reset (folder deleted, record removed)."
        
        elif target_step == "transcribe":
            # 重做轉錄: 刪除 srt, txt, proofread, reports (保留媒體檔)
            patterns = ["*.srt", "*.txt", "*_proofread.srt", "*.xlsx", "*.docx"]
            for p in patterns:
                for f in glob.glob(os.path.join(ep_dir, p)):
                    os.remove(f)
            message = f"Transcription and subsequent steps reset for {video_id}."
            
        elif target_step == "proofread":
            # 重做校對: 刪除 proofread srt, reports
            patterns = ["*_proofread.srt", "*.xlsx", "*.docx"]
            for p in patterns:
                for f in glob.glob(os.path.join(ep_dir, p)):
                    os.remove(f)
            message = f"Proofreading and subsequent steps reset for {video_id}."
            
        elif target_step == "report":
            # 重做報告: 刪除 reports
            patterns = ["*.xlsx", "*.docx"]
            for p in patterns:
                for f in glob.glob(os.path.join(ep_dir, p)):
                    os.remove(f)
            message = f"Reports reset for {video_id}."
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid target_step: {target_step}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute redo: {e}")

    # 寫回 JSON (如果是 download/None 則 processed 已更新)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=4)

    return {"status": "success", "message": message}



@app.post("/api/url/detect")
async def detect_url(req: Request):
    """自動判別 URL 是單一影片還是播放清單，並取得名稱。"""
    data = await req.json()
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        # Use --flat-playlist to get metadata without downloading videos
        result = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-single-json", "--no-warnings", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise Exception(result.stderr or "yt-dlp failed")

        info = json.loads(result.stdout)
        
        # Check if it's a playlist or a single video
        _type = info.get("_type", "video")
        title = info.get("title", "")
        
        if _type == "playlist":
            entries = info.get("entries", [])
            count = len(entries)
            return {"type": "playlist", "count": count, "title": title}
        else:
            return {"type": "video", "count": 1, "title": title}

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="yt-dlp timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard")
def get_dashboard():
    """Per-playlist dashboard stats cross-referencing processed_videos.json."""
    # Reload playlists
    playlist_manager._config = playlist_manager._load_config()
    all_playlists = playlist_manager.playlists

    # Load processed videos
    json_path = os.path.join(BASE_DIR, "processed_videos.json")
    processed = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                processed = json.load(f)
            except Exception:
                pass

    # Dynamically detect proofread status from NAS disk (same logic as /api/status)
    nas_base = DEFAULT_CONFIG.get("nas_output_base", "/mnt/nas/Whisper_auto_rum/T097V")
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
                nas_base = cfg.get("nas_output_base", nas_base)
        except Exception:
            pass

    import re, glob
    for vid, info in processed.items():
        if info.get("proofread"):
            continue
        
        # Determine the effective output_dir and prefix for this video
        pl_id = info.get("playlist_id")
        target_dir = os.path.join(nas_base, "T097V")
        prefix = "T097V" # Default
        
        if pl_id:
            matching_pl = next((p for p in all_playlists if p.get("id") == pl_id), None)
            if matching_pl:
                prefix = matching_pl.get("folder_prefix", "T097V")
                target_dir = os.path.join(nas_base, prefix)
        
        title = info.get("title", "")
        # Try to find episode number (last digits in title)
        match = re.search(r'(\d+)\s*$', title)
        if not match:
            continue
            
        ep = str(int(match.group(1))).zfill(3)
        ep_dir = os.path.join(target_dir, f"{prefix}{ep}")
        
        if os.path.isdir(ep_dir):
            proofread_files = glob.glob(os.path.join(ep_dir, "*_proofread.srt"))
            if proofread_files:
                info["proofread"] = True

    # Group videos by playlist_id
    playlist_videos: dict[str, list] = {}
    legacy_videos: list = []
    for vid, info in processed.items():
        pl_id = info.get("playlist_id")
        if pl_id:
            playlist_videos.setdefault(pl_id, []).append({**info, "video_id": vid})
        else:
            legacy_videos.append({**info, "video_id": vid})

    # Build per-playlist summary
    playlist_summaries = []
    for pl in all_playlists:
        pl_id = pl.get("id", "")
        videos = playlist_videos.get(pl_id, [])
        whispered = len(videos)
        proofread = sum(1 for v in videos if v.get("proofread"))
        last_time = ""
        if videos:
            times = [v.get("processed_at", "") for v in videos if v.get("processed_at")]
            if times:
                last_time = max(times)
        playlist_summaries.append({
            "id": pl_id,
            "name": pl.get("name", ""),
            "url": pl.get("url", ""),
            "enabled": pl.get("enabled", True),
            "whisper_model": pl.get("whisper_model", "large-v3"),
            "status": pl.get("status", "idle"),
            "batch_size": pl.get("batch_size", 5),
            "whisper_lang": pl.get("whisper_lang", "auto"),
            "whisper_prompt": pl.get("whisper_prompt", ""),
            "lecture_pdf": pl.get("lecture_pdf", ""),
            "total_videos": pl.get("total_videos", 0),
            "stats": {
                "whispered": whispered,
                "proofread": proofread,
                "pending": pl.get("total_videos", 0) - proofread,
            },
            "last_processed_at": last_time,
            "videos": videos,
        })

    # Determine if we should show a legacy section.
    has_explicit_legacy = any(pl.get("id") == "__legacy__" for pl in all_playlists)

    if legacy_videos and not has_explicit_legacy:
        legacy_whispered = len(legacy_videos)
        legacy_proofread = sum(1 for v in legacy_videos if v.get("proofread"))
        legacy_times = [v.get("processed_at", "") for v in legacy_videos if v.get("processed_at")]
        legacy_last = max(legacy_times) if legacy_times else ""
        playlist_summaries.insert(0, {
            "id": "__legacy__",
            "name": "佛教公案選集",
            "url": "",
            "enabled": True,
            "whisper_model": "",
            "total_videos": legacy_whispered,
            "stats": {
                "whispered": legacy_whispered,
                "proofread": legacy_proofread,
                "pending": legacy_whispered - legacy_proofread,
            },
            "last_processed_at": legacy_last,
            "videos": legacy_videos,
        })

    # Include NotebookLM status
    try:
        scheduler = _get_nlm_scheduler()
        nlm_summary = scheduler.get_queue_summary()
        by_status = nlm_summary.get("by_status", {})
        nlm_status_data = {
            "total_quota": nlm_summary.get("quota", {}).get("total", 50),
            "used_quota": nlm_summary.get("quota", {}).get("used", 0),
            "remaining_quota": nlm_summary.get("quota", {}).get("remaining", 50),
            "queue_size": nlm_summary.get("total", 0),
            "active_tasks": by_status.get("running", 0),
        }
    except Exception:
        nlm_status_data = None

    # For each video, also check NotebookLM outputs
    for pl in playlist_summaries:
        for v in pl.get("videos", []):
            title = v.get("title", "")
            match = re.search(r'(\d+)\s*$', title)
            if match:
                prefix = pl.get("folder_prefix", "T097V")
                ep = str(int(match.group(1))).zfill(3)
                nlm_dir = os.path.join(nas_base, prefix, f"{prefix}{ep}", "notebooklm")
                if os.path.exists(nlm_dir):
                    v["notebooklm_output"] = {
                        "mindmap": os.path.exists(os.path.join(nlm_dir, f"{prefix}{ep}_mindmap.md")),
                        "presentation": os.path.exists(os.path.join(nlm_dir, f"{prefix}{ep}_presentation.md")),
                        "summary": os.path.exists(os.path.join(nlm_dir, f"{prefix}{ep}_summary.md")),
                        "infographic_standard": os.path.exists(os.path.join(nlm_dir, f"{prefix}{ep}_infographic_full.md")),
                        "infographic_compact": os.path.exists(os.path.join(nlm_dir, f"{prefix}{ep}_infographic_compact.md")),
                    }

    total_videos = len(processed)
    total_proofread = sum(1 for v in processed.values() if v.get("proofread"))

    return {
        "playlists": playlist_summaries,
        "global_stats": {
            "total_playlists": len(all_playlists),
            "active_playlists": len([p for p in all_playlists if p.get("enabled", True)]),
            "total_videos": total_videos,
            "total_proofread": total_proofread,
        },
        "notebooklm": nlm_status_data
    }

# -------------------------------

@app.get("/api/status")
def get_status():
    json_path = os.path.join(BASE_DIR, "processed_videos.json")
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            return {}

    # 載入設定取得 NAS 路徑
    nas_base = DEFAULT_CONFIG.get("nas_output_base", "/mnt/nas/Whisper_auto_rum/T097V")
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
                nas_base = cfg.get("nas_output_base", nas_base)
        except Exception:
            pass

    # 動態檢查磁碟上的校對檔案，補全 proofread 狀態
    import re, glob
    for vid, info in data.items():
        if info.get("proofread"):
            continue
        title = info.get("title", "")
        match = re.search(r'(\d+)\s*$', title)
        if match:
            ep = str(int(match.group(1))).zfill(3)
        else:
            continue
        # For /api/status, use default prefix logic
        ep_dir = os.path.join(nas_base, "T097V", f"T097V{ep}")
        if os.path.isdir(ep_dir):
            proofread_files = glob.glob(os.path.join(ep_dir, "*_proofread.srt"))
            if proofread_files:
                info["proofread"] = True

    return data

def tail(filename, n=100):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return f.readlines()[-n:]

@app.get("/api/logs/{log_type}")
def get_logs(log_type: str):
    log_map = {
        "proofread": "youtube_whisper.log",
        "whisper": "youtube_whisper.log",
        "cron": "youtube_whisper.log",
        "meeting": "meeting_process.log"
    }
    filename = log_map.get(log_type)
    if not filename:
        return {"error": "Invalid log type"}
    return {"lines": tail(os.path.join(BASE_DIR, filename))}

@app.get("/api/stream/{log_type}")
async def stream_logs(log_type: str, request: Request):
    log_map = {
        "proofread": "youtube_whisper.log",
        "whisper": "youtube_whisper.log",
        "cron": "youtube_whisper.log",
        "meeting": "meeting_process.log"
    }
    filename = log_map.get(log_type)
    if not filename:
        return HTMLResponse("Invalid log type", status_code=400)
        
    filepath = os.path.join(BASE_DIR, filename)

    async def log_generator():
        if not os.path.exists(filepath):
            yield f"data: File {filename} not found\n\n"
            return
            
        with open(filepath, "r", encoding="utf-8") as f:
            # Read all lines and yield the last 200 to give user context
            lines = f.readlines()
            for line in lines[-200:]:
                yield f"data: {line.rstrip(chr(10))}\n\n"
            
            # Now wait for new lines
            while True:
                if await request.is_disconnected():
                    break
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                yield f"data: {line.rstrip(chr(10))}\n\n"

    return StreamingResponse(log_generator(), media_type="text/event-stream")

class TaskRequest(BaseModel):
    action: str
    target: str
    title: str | None = None
    source: str | None = None

def _is_whisper_running() -> bool:
    """透過共用 GPU 鎖判斷是否有轉錄行程正在執行。"""
    return is_gpu_busy()


@app.get("/api/task/status")
def get_task_status():
    """查詢目前是否有 GPU 任務正在執行（Whisper / 月會聽打等）。"""
    return {"whisper_running": is_gpu_busy()}


@app.get("/api/queue/status")
def get_queue_status():
    """查詢任務佇列與排程器狀態。"""
    with get_session() as session:
        repo = TaskRepository(session)
        pending = repo.count_pending_stages()
        running = repo.get_running_stages()

    return {
        "scheduler_running": _scheduler is not None and _scheduler._running,
        "pending_stages": pending,
        "running_stages": len(running),
        "gpu_busy": is_gpu_busy(),
    }


@app.post("/api/task")
def manage_task(req: TaskRequest):
    if req.action == "queue":
        # 新增：佇列式任務提交 → 寫入 SQLite
        if not req.target:
            return {"error": "Target (video_id) required"}
        title = req.title or req.target
        source_str = req.source or "external"
        source = TaskSource.INTERNAL if source_str == "internal" else TaskSource.EXTERNAL
        with get_session() as session:
            repo = TaskRepository(session)
            task = repo.create_task(
                title=title,
                video_id=req.target,
                source=source,
            )
            stage = create_initial_stages(session, task)
        return {
            "status": "queued",
            "task_id": task.id,
            "stage_id": stage.id,
            "video_id": req.target,
        }
    elif req.action == "proofread":
        if not req.target:
            return {"error": "Target required"}
        python_bin = os.path.join(BASE_DIR, "venv", "bin", "python3")
        cmd = [python_bin, "-u", os.path.join(BASE_DIR, "auto_proofread.py"), req.target]
        log_file = open(os.path.join(BASE_DIR, "youtube_whisper.log"), "a", encoding="utf-8")
        subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
        return {"status": "started", "cmd": cmd}
    elif req.action == "whisper":
        # 啟動前先確認無現存 Whisper 行程，防止 VRAM/RAM 耗盡導致 VM 崩潰
        if _is_whisper_running():
            return {"status": "busy", "message": "Whisper 任務正在執行中，請稍後再試"}
        python_bin = os.path.join(BASE_DIR, "venv", "bin", "python3")
        cmd = [python_bin, "-u", os.path.join(BASE_DIR, "auto_youtube_whisper.py")]
        log_file = open(os.path.join(BASE_DIR, "youtube_whisper.log"), "a", encoding="utf-8")
        subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
        return {"status": "started", "cmd": cmd}
    return {"error": "Unknown action"}


# ---------------------------------------------------------------
# NotebookLM Post-Processing Endpoints
# ---------------------------------------------------------------

NLM_QUEUE_FILE = os.path.join(BASE_DIR, "notebooklm_queue.json")


def _get_nlm_scheduler() -> NotebookLMScheduler:
    """Construct a scheduler using current config (no side effects)."""
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    nlm_cfg = cfg.get("notebooklm", {})
    notebook_url = nlm_cfg.get("notebook_url", "")
    daily_quota = nlm_cfg.get("daily_quota_per_account", 50)
    client = NotebookLMClient(daily_quota=daily_quota)
    return NotebookLMScheduler(
        queue_file=NLM_QUEUE_FILE,
        notebook_url=notebook_url,
        client=client,
        daily_quota=daily_quota,
    )


@app.get("/api/notebooklm/status")
def nlm_status():
    """NotebookLM 佇列與 quota 狀態。"""
    scheduler = _get_nlm_scheduler()
    summary = scheduler.get_queue_summary()
    by_status = summary.get("by_status", {})
    return {
        "quota": summary["quota"],
        "queue": {
            "total": summary["total"],
            "pending": by_status.get("pending", 0),
            "running": by_status.get("running", 0),
            "completed": by_status.get("completed", 0),
            "failed": by_status.get("failed", 0),
        },
    }


@app.get("/api/notebooklm/quota")
def nlm_quota():
    """NotebookLM 今日配額詳細。"""
    scheduler = _get_nlm_scheduler()
    return scheduler.client.get_quota_info()


@app.get("/api/notebooklm/queue")
def nlm_queue():
    """NotebookLM 佇列內容。"""
    scheduler = _get_nlm_scheduler()
    return {"items": scheduler.get_queue_items()}


class NlmTriggerReq(BaseModel):
    episode: str = ""  # Optional: e.g. 'T097V017'. Empty = all eligible.
    tasks: list[str] = []  # Optional: specific output types


@app.post("/api/notebooklm/trigger")
def nlm_trigger(req: NlmTriggerReq):
    """Trigger NotebookLM 後製（失程剔 subprocess）。"""
    python_bin = os.path.join(BASE_DIR, "venv", "bin", "python3")
    cmd = [python_bin, "-u", os.path.join(BASE_DIR, "auto_notebooklm.py")]
    if req.episode:
        cmd += ["--episode", req.episode]
    if req.tasks:
        for task in req.tasks:
            cmd += ["--task", task]

    log_path = os.path.join(BASE_DIR, "notebooklm.log")
    log_file = open(log_path, "a", encoding="utf-8")
    subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
    return {"status": "success", "message": "NotebookLM 後製任務已啟動"}


@app.get("/api/notebooklm/outputs/{episode_folder}")
def nlm_outputs(episode_folder: str):
    """Get NotebookLM output files for a specific episode."""
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    nas_base = cfg.get("nas_output_base", "/mnt/nas/Whisper_auto_rum")
    # episode_folder is like 'T097V017' — detect prefix from first 5 chars
    prefix = episode_folder[:5] if len(episode_folder) >= 5 else episode_folder
    ep_dir = os.path.join(nas_base, prefix, episode_folder)
    nlm_dir = os.path.join(ep_dir, "notebooklm")

    if not os.path.isdir(nlm_dir):
        return {"episode": episode_folder, "files": []}

    files = [
        {
            "filename": fname,
            "type": _detect_output_type(fname),
            "size_bytes": os.path.getsize(os.path.join(nlm_dir, fname)),
        }
        for fname in sorted(os.listdir(nlm_dir))
        if fname.endswith(".md")
    ]
    return {"episode": episode_folder, "files": files}


def _detect_output_type(filename: str) -> str:
    """Detect output type from filename suffix."""
    suffixes = {
        "_mindmap.md": "心智圖",
        "_presentation.md": "簡報",
        "_summary.md": "影片摘要",
        "_infographic_full.md": "資訊圖表標準",
        "_infographic_compact.md": "資訊圖表精簡",
    }
    for suffix, label in suffixes.items():
        if filename.endswith(suffix):
            return label
    return "未知"


@app.get("/api/notebooklm/download")
def nlm_download(episode: str, filename: str):
    """Serve a specific NotebookLM output file by filename."""
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    nas_base = cfg.get("nas_output_base", "/mnt/nas/Whisper_auto_rum")
    prefix = episode[:5]
    ep_dir = os.path.join(nas_base, prefix, episode)
    file_path = os.path.join(ep_dir, "notebooklm", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file_path, filename=filename, media_type="text/markdown")


@app.get("/api/notebooklm/logs")
def nlm_logs():
    """Get last 200 lines from notebooklm.log."""
    return {"lines": tail(os.path.join(BASE_DIR, "notebooklm.log"), 200)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

import asyncio
import json
import os
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        ep_dir = os.path.join(nas_base, f"T097V{ep}")
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
        "proofread": "auto_proofread.log",
        "whisper": "auto_youtube_whisper.log",
        "cron": "auto_youtube_whisper_cron.log"
    }
    filename = log_map.get(log_type)
    if not filename:
        return {"error": "Invalid log type"}
    return {"lines": tail(os.path.join(BASE_DIR, filename))}

@app.get("/api/stream/{log_type}")
async def stream_logs(log_type: str, request: Request):
    log_map = {
        "proofread": "auto_proofread.log",
        "whisper": "auto_youtube_whisper.log",
        "cron": "auto_youtube_whisper_cron.log"
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

@app.post("/api/task")
def manage_task(req: TaskRequest):
    if req.action == "proofread":
        if not req.target:
            return {"error": "Target required"}
        cmd = ["python3", os.path.join(BASE_DIR, "auto_proofread.py"), req.target]
        subprocess.Popen(cmd, cwd=BASE_DIR)
        return {"status": "started", "cmd": cmd}
    return {"error": "Unknown action"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

#!/usr/bin/env python3
"""
YouTube 播放清單自動追蹤 + Whisper 辨識 + Gemini 校對 + Email 通知
=====================================================
追蹤指定 YouTube 播放清單，偉測新影片後自動下載音訊、
使用 Whisper large-v2 進行語音辨識，後由 Gemini Pro 校對字幕，完成後發送 Email 通知。

用法:
    python auto_youtube_whisper.py           # 正常執行
    python auto_youtube_whisper.py --dry-run # 僅列出新影片，不下載/辨識
"""

import time
import os
import torch
import sys
import re
import json
import subprocess
import smtplib
import logging
import argparse
import glob
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from gpu_lock import acquire_gpu_lock, release_gpu_lock

# 并发控制：各階段信號量 (Semaphores)
# 限制 GPU 同時存取數 (RTX 5070 Ti 16GB, large-v3 建議為 1)
gpu_semaphore = threading.Semaphore(1)
# 限制 Gemini API 同時請求數 (避免 Rate Limit)
api_semaphore = threading.Semaphore(2)
# 限制同時下載數 (避免網路頻寬佔盡)
dl_semaphore = threading.Semaphore(3)
# 進度檔存取鎖，確保多執行緒寫入正確
state_lock = threading.Lock()

# faster-whisper (CTranslate2 加速，比 openai-whisper CLI 快約 4x)
try:
    from faster_whisper import WhisperModel as FasterWhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

# 匯入校對模組
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
try:
    from auto_proofread import load_lecture_text, proofread_srt, build_srt
    PROOFREAD_AVAILABLE = True
except ImportError:
    PROOFREAD_AVAILABLE = False

# ================= 設定區域 =================

from pipeline.playlist_manager import PlaylistManager

# 工作目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 載入設定檔 (config.json)
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
config_data = {}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"無法讀取 config.json: {e}")

# 播放清單 URL & NAS 路徑
PLAYLIST_URL = config_data.get("playlist_url", "https://www.youtube.com/playlist?list=PLpyk9ZaUyAgGLftJLKQQefuK0bDV3iV73")
NAS_OUTPUT_BASE = config_data.get("nas_output_base", "/mnt/nas/Whisper_auto_rum/T097V")

STATE_FILE = os.path.join(BASE_DIR, "processed_videos.json")

# yt-dlp 設定：優先使用 venv 內的最新版本，避免系統版本過舊問題
_venv_ytdlp = os.path.join(BASE_DIR, "venv", "bin", "yt-dlp")
YTDLP_BIN = _venv_ytdlp if os.path.exists(_venv_ytdlp) else "/usr/local/bin/yt-dlp"
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

# Whisper 設定
WHISPER_BIN = os.path.join(BASE_DIR, "venv", "bin", "whisper")
WHISPER_MODEL = config_data.get("whisper_model", "large-v2")
WHISPER_LANG = config_data.get("whisper_lang", "Chinese")
WHISPER_PROMPT = config_data.get("whisper_prompt", "佛教公案選集 不要標點符號 ")

# Email 設定
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "bbudaedu@gmail.com"
EMAIL_PASS = "khwvartcqbgztwgr"
_email_raw = config_data.get("email_to", "")
if _email_raw:
    EMAIL_TO = [e.strip() for e in _email_raw.split(",") if e.strip()]
else:
    EMAIL_TO = []

# ==========================================

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
    force=True,  # Ensure handlers are applied even if root logger was pre-configured
)
logger = logging.getLogger(__name__)


def setup_directories():
    """建立所需目錄"""
    os.makedirs(NAS_OUTPUT_BASE, exist_ok=True)

# ===== 語言代碼對應表 (供 faster-whisper 使用) =====
LANGUAGE_MAP = {
    "chinese": "zh",
    "english": "en",
    "japanese": "ja",
    "korean": "ko",
    "french": "fr",
    "spanish": "es",
    "german": "de",
    "burmese": "my",
    "taiwanese": "zh", # 臺灣話對應到中文，讓 Whisper 理解為中文語系
}

def get_whisper_lang_code(lang_str):
    """將常見語言名稱轉換為 faster-whisper (ISO-639-1) 接受的代碼"""
    if not lang_str:
        return None
    lang = str(lang_str).strip().lower()
    if lang == "auto" or lang == "":
        return None
    return LANGUAGE_MAP.get(lang, lang_str)


def _calculate_episode_dir(title, prefix="T097V"):
    """內部輔助函式：強制路徑結構為 基礎路徑/資料夾前綴/資料夾前綴+集數"""
    # 從標題末尾提取數字
    match = re.search(r'(\d+)\s*$', title)
    if match:
        episode_num = str(int(match.group(1))).zfill(3)  # 補足三位數: '1' -> '001'
    else:
        # 無法提取集數，使用全標題
        episode_num = title.strip().replace(' ', '_')

    # 強制使用 NAS_OUTPUT_BASE 作為根路徑
    target_base = NAS_OUTPUT_BASE.rstrip(os.sep)
    
    # 組合路徑：NAS_OUTPUT_BASE / PREFIX / PREFIX###
    series_dir = os.path.join(target_base, prefix)
    episode_dir = os.path.join(series_dir, f"{prefix}{episode_num}")
    
    return episode_dir


def get_episode_dir(title, prefix="T097V"):
    """建立影片集數對應資料夾路徑 (固定結構)"""
    episode_dir = _calculate_episode_dir(title, prefix=prefix)
    os.makedirs(episode_dir, exist_ok=True)
    logger.info(f"集數目錄: {episode_dir}")
    return episode_dir


def load_processed_videos():
    """載入已處理影片清單"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # 轉換舊的格式 (List) -> 新的格式 (Dictionary)
                    migrated = {}
                    for item in data:
                        if isinstance(item, str):
                            migrated[item] = {"title": item, "processed_at": "N/A"}
                    return migrated
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"無法讀取狀態檔，將重新建立: {e}")
    return {}


def save_processed_videos(processed):
    """儲存已處理影片清單"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
    logger.info(f"已更新狀態檔: {STATE_FILE}")


def get_playlist_videos():
    """使用 yt-dlp 取得播放清單中所有影片資訊"""
    logger.info(f"正在取得播放清單資訊: {PLAYLIST_URL}")

    cmd = [
        YTDLP_BIN,
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        "--js-runtimes", "node",
        "--cookies", COOKIES_FILE,
        PLAYLIST_URL,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        logger.error("取得播放清單逾時 (120秒)")
        return []
    except subprocess.CalledProcessError as e:
        logger.error(f"取得播放清單失敗: {e.stderr}")
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            info = json.loads(line)
            video_id = info.get("id", "")
            title = info.get("title", "Unknown")
            url = info.get("url", "") or f"https://www.youtube.com/watch?v={video_id}"
            if video_id:
                videos.append({"id": video_id, "title": title, "url": url})
        except json.JSONDecodeError:
            continue

    logger.info(f"播放清單共有 {len(videos)} 部影片")
    return videos


def _build_doc_prefix(safe_title: str, video_id: str) -> str:
    """Build document prefix for docx filenames. Shared by check_video_files_exist and process_video."""
    title_part = f"{safe_title}__{video_id}".split('__')[0]
    match = re.search(r'佛教公案選集\s*簡豐文居士\s*(\d+)', title_part)
    if match:
        ep_num = match.group(1)
        return f"佛教公案選集{ep_num}_簡豐文居士"
    return title_part.replace(" ", "_")[:25]


def check_video_files_exist(title, video_id, prefix="T097V", output_base=None):
    """檢查預期的輸出檔案是否已經存在 (完整的 Pipeline 產出，包含報表)"""
    if output_base is None:
        output_base = NAS_OUTPUT_BASE
    # 取得預期的集數編號 (用於 Legacy 檔名檢查)
    match = re.search(r'(\d+)\s*$', title)
    episode_num = str(int(match.group(1))).zfill(3) if match else title.strip().replace(' ', '_')
    
    # 取得預期目錄 (使用統一邏輯)
    episode_dir = _calculate_episode_dir(title, prefix=prefix)
    
    # 取得安全檔名
    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
    ).strip()
    if not safe_title:
        safe_title = video_id
        
    import glob
    existing_txts = glob.glob(os.path.join(episode_dir, "*.txt"))
    existing_srts = [f for f in glob.glob(os.path.join(episode_dir, "*.srt")) if not f.endswith("_proofread.srt")]
    expected_proofreads = glob.glob(os.path.join(episode_dir, "*_proofread.srt"))
    
    # 報表路徑 (use shared helper to guarantee naming consistency)
    doc_prefix = _build_doc_prefix(safe_title, video_id)
        
    expected_xlsx = os.path.join(episode_dir, f"{safe_title}__{video_id}.xlsx")
    expected_docx_student = os.path.join(episode_dir, f"{doc_prefix}給學員校對.docx")
    expected_docx_ai = os.path.join(episode_dir, f"{doc_prefix}校對文本.docx")

    # 預期的舊檔名 (Legacy) -> 也就是 "T097V001" 類似的前綴
    legacy_base = f"{prefix}{episode_num}"
    legacy_xlsx = os.path.join(episode_dir, f"{legacy_base}.xlsx")
    legacy_docx_student = os.path.join(episode_dir, f"{legacy_base}給學員校對.docx")
    legacy_docx_ai = os.path.join(episode_dir, f"{legacy_base}校對文本.docx")

    # 檢查是否具有辨識結果
    has_whisper = bool(existing_txts and existing_srts)
    
    if not has_whisper:
        return False
        
    # 只要符合新檔名或舊檔名任一即可
    has_xlsx = os.path.exists(expected_xlsx) or os.path.exists(legacy_xlsx)
    has_docx_student = os.path.exists(expected_docx_student) or os.path.exists(legacy_docx_student)
    has_docx_ai = os.path.exists(expected_docx_ai) or os.path.exists(legacy_docx_ai)

    # 如果具有 Whisper 結果，且不要求有報表與校對，或者具有所有要求的檔案
    # 目前我們希望檢查「所有完整流程檔案」，包含校對與三份報表
    has_proofread = bool(expected_proofreads) and has_xlsx and has_docx_student and has_docx_ai
                    
    # 但如果 PROOFREAD 根本沒開，有 Whisper 就夠了 (後續會 skip proofread)
    if not PROOFREAD_AVAILABLE:
        return True
        
    return has_proofread

def find_new_videos(all_videos, processed, playlist_id="", prefix="T097V", output_base=None):
    """找出尚未處理的新影片，並加上雙重防呆：檢查實體檔案是否存在"""
    new_videos = []
    missing_in_json_but_done = []
    
    # Sort videos sequentially based on number in title to ensure we start from the oldest
    def extract_number(title):
        match = re.search(r'(\d+)\s*$', title)
        return int(match.group(1)) if match else 0
        
    sorted_videos = sorted(all_videos, key=lambda x: extract_number(x["title"]))
    
    for v in sorted_videos:
        video_id = v["id"]
        title = v["title"]
        
        # 檢查 NAS 目錄是否有完整的實體檔案存在 (包含 Whisper、校對、報表)
        files_complete = check_video_files_exist(title, video_id, prefix=prefix, output_base=output_base)
        
        if video_id in processed:
            if files_complete:
                continue # JSON 有紀錄且檔案完整，安全跳過
            else:
                logger.info(f"發現 [{video_id}] {title} 在記錄中但實體檔案(或報表)不完整，排入補齊流程。")
                new_videos.append(v)
                continue
                
        # JSON 沒有紀錄，但檔案居然完整存在？
        if files_complete:
            logger.info(f"警告: [{video_id}] {title} 檔案已完整存在，但未記錄在進度檔中，強制跳過並補回。")
            missing_in_json_but_done.append(v)
            continue
            
        new_videos.append(v)
        
    # 自動修復遺漏的記錄
    if missing_in_json_but_done:
        for v in missing_in_json_but_done:
            processed[v["id"]] = {
                "title": v["title"],
                "processed_at": datetime.now().isoformat() + "_recovered",
                "srt": "recovered from disk",
                "txt": "recovered from disk",
                "playlist_id": playlist_id
            }
        save_processed_videos(processed)

    if new_videos:
        logger.info(f"發現 {len(new_videos)} 部新影片待處理")
        for v in new_videos:
            logger.info(f"  - [{v['id']}] {v['title']}")
    else:
        logger.info("沒有新影片")
    return new_videos


def download_audio(video, episode_dir):
    """下載影片音訊為 WAV 16kHz mono (Whisper 最佳格式)"""
    video_id = video["id"]
    title = video["title"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    logger.info(f"正在下載音訊: {title}")

    # 使用安全的檔名
    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
    ).strip()
    if not safe_title:
        safe_title = video_id
        
    # 尋找已存在的 WAV 檔案
    pattern = os.path.join(episode_dir, f"{safe_title}__{video_id}.*")
    matches = glob.glob(pattern)
    wav_files = [m for m in matches if m.endswith(".wav")]
    if wav_files:
        logger.info(f"發現已下載的音訊，跳過下載: {wav_files[0]}")
        return wav_files[0]

    output_template = os.path.join(episode_dir, f"{safe_title}__{video_id}.%(ext)s")

    cmd = [
        YTDLP_BIN,
        "-x",                      # 僅提取音訊
        "--audio-format", "wav",    # 轉為 WAV
        "--postprocessor-args",
        "ffmpeg:-ar 16000 -ac 1",   # 16kHz mono (Whisper 原生取樣率)
        "--js-runtimes", "node",    # 使用 Node.js 解析 YouTube
        "--cookies", COOKIES_FILE,  # YouTube 認證 cookies
        "-o", output_template,
        "--no-playlist",
        video_url,
    ]

    try:
        with dl_semaphore:
            subprocess.run(cmd, check=True, timeout=600)
    except subprocess.TimeoutExpired:
        logger.error(f"下載逾時 (600秒): {title}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"下載失敗: {title} - {e}")
        return None

    # 找到下載的 WAV 檔案
    pattern = os.path.join(episode_dir, f"{safe_title}__{video_id}.*")
    matches = glob.glob(pattern)
    wav_files = [m for m in matches if m.endswith(".wav")]

    if wav_files:
        wav_path = wav_files[0]
        logger.info(f"下載完成: {wav_path}")
        return wav_path
    else:
        logger.error(f"找不到下載的 WAV 檔: {pattern}")
        # 嘗試找任何音訊檔
        if matches:
            logger.info(f"找到其他格式: {matches[0]}")
            return matches[0]
        return None


# 行程層級模型快取（同一次執行多集時只載入一次）
_whisper_model_cache: dict = {}


def _get_whisper_model(model_name: str) -> "FasterWhisperModel":
    """取得（或建立）快取的 faster-whisper WhisperModel 實例"""
    if model_name not in _whisper_model_cache:
        logger.info(f"載入 faster-whisper 模型: {model_name} (float16, CUDA)")
        _whisper_model_cache[model_name] = FasterWhisperModel(
            model_name,
            device="cuda",
            compute_type="float16",  # RTX 5070 Ti 支援 float16，精度佳
        )
    return _whisper_model_cache[model_name]


def _write_srt(segments, path: str):
    """將 faster-whisper segments 列表寫成標準 SRT 格式"""
    def _fmt_ts(t: float) -> str:
        h, rem = divmod(int(t), 3600)
        m, s = divmod(rem, 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}\n{seg.text.strip()}\n\n")


def run_whisper(audio_path, episode_dir, whisper_model, whisper_lang, whisper_prompt):
    """使用 faster-whisper Python API 進行語音辨識（比 CLI 快約 4x，VRAM 省約 50%）"""
    basename = os.path.splitext(os.path.basename(audio_path))[0]
    srt_path = os.path.join(episode_dir, f"{basename}.srt")
    txt_path = os.path.join(episode_dir, f"{basename}.txt")

    # 已有辨識結果則跳過
    if os.path.exists(srt_path) and os.path.exists(txt_path):
        logger.info(f"發現已完成的辨識結果，跳過: {srt_path}")
        return {"srt": srt_path, "txt": txt_path, "basename": basename}

    if not FASTER_WHISPER_AVAILABLE:
        logger.error("faster-whisper 未安裝，請執行: pip install faster-whisper")
        return None

    logger.info(f"正在執行 faster-whisper 辨識: {basename}")
    try:
        with gpu_semaphore:
            model = _get_whisper_model(whisper_model)
            lang_code = get_whisper_lang_code(whisper_lang)
            logger.info(f"使用模型: {whisper_model}, 語言: {lang_code if lang_code else 'Auto'}, Prompt: {whisper_prompt}")
            
            segments_gen, info = model.transcribe(
                audio_path,
                language=lang_code,
                initial_prompt=whisper_prompt,
                vad_filter=True,   # 過濾靜音段，減少幻覺
                beam_size=5,
            )
            # 將 generator 轉為 list（才能重複使用）
            segments = list(segments_gen)
        logger.info(f"辨識完成，共 {len(segments)} 段，語言: {info.language} (機率: {info.language_probability:.2f})")
    except Exception as e:
        logger.error(f"faster-whisper 辨識失敗: {e}")
        return None

    # 輸出 SRT
    _write_srt(segments, srt_path)
    # 輸出 TXT（純文字）
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(seg.text.strip() for seg in segments))

    logger.info(f"輸出 SRT: {srt_path}")
    logger.info(f"輸出 TXT: {txt_path}")
    return {"srt": srt_path, "txt": txt_path, "basename": basename}


def send_email(subject, body, attachment_paths=None):
    """發送 Email 通知"""
    if not EMAIL_TO:
        logger.error("未設定收件人信箱 (config.json 中的 email_to 欄位為空)，跳過 Email 發送")
        return False
        
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(EMAIL_TO)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 附加檔案
    if attachment_paths:
        for path in attachment_paths:
            if path and os.path.exists(path):
                filename = os.path.basename(path)
                try:
                    with open(path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=('utf-8', '', filename)
                    )
                    msg.attach(part)
                except Exception as e:
                    logger.warning(f"無法附加檔案 {filename}: {e}")

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        server.quit()
        logger.info(f"Email 已發送至 {EMAIL_TO}")
        return True
    except Exception as e:
        logger.error(f"Email 發送失敗: {e}")
        return False


def process_video(video, pl_config):
    """處理單一影片: 下載 -> Whisper 辨識 -> Email 通知"""
    video_id = video["id"]
    title = video["title"]
    actually_did_work = False  # Track whether we did real processing (not just skipped)

    logger.info(f"{'='*60}")
    logger.info(f"開始處理: [{video_id}] {title}")
    logger.info(f"{'='*60}")

    # 0. 建立該集的輸出資料夾 (例: /mnt/nas/Whisper_auto_rum/T097V/T097V11)
    prefix = pl_config.get("folder_prefix", "T097V")
    output_dir = pl_config.get("output_dir")
    episode_dir = get_episode_dir(title, prefix=prefix)

    # 1. 下載音訊到該集資料夾
    # 獲取安全文件名以檢查
    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
    ).strip()
    if not safe_title: safe_title = video_id
    
    import glob
    existing_audios = glob.glob(os.path.join(episode_dir, "*.wav")) + glob.glob(os.path.join(episode_dir, "*.mp4"))
    
    if existing_audios:
        logger.info(f"發現音訊檔案已存在，跳過下載: {existing_audios[0]}")
        audio_path = existing_audios[0]
    else:
        if not PLAYLIST_URL:
            logger.error(f"找不到本地音訊檔案，且缺乏播放清單 URL 可供下載: {title}")
            return {"success": False, "error": "缺乏音訊來源，無法下載"}
        audio_path = download_audio(video, episode_dir)
        actually_did_work = True
        
    if not audio_path:
        return {"success": False, "error": "下載失敗"}

    # 取出各清單專屬的辨識設定
    whisper_model_pl = pl_config.get("whisper_model", "large-v3")
    whisper_lang_pl = pl_config.get("whisper_lang", "auto")
    whisper_prompt_pl = pl_config.get("whisper_prompt", "")
    proofread_prompt_pl = pl_config.get("proofread_prompt", "")
    lecture_pdf_pl = pl_config.get("lecture_pdf", "")

    # 2. Whisper 辨識，輸出到該集資料夾
    existing_txts = glob.glob(os.path.join(episode_dir, "*.txt"))
    existing_srts = [f for f in glob.glob(os.path.join(episode_dir, "*.srt")) if not f.endswith("_proofread.srt")]
    
    if existing_txts and existing_srts:
        logger.info(f"發現 Whisper 辨識結果已存在，跳過轉錄: {existing_txts[0]}")
        whisper_result = {"txt": existing_txts[0], "srt": existing_srts[0], "success": True}
    else:
        whisper_result = run_whisper(
            audio_path, 
            episode_dir, 
            whisper_model=whisper_model_pl, 
            whisper_lang=whisper_lang_pl, 
            whisper_prompt=whisper_prompt_pl
        )
        actually_did_work = True
    if not whisper_result:
        return {"success": False, "error": "Whisper 辨識失敗"}

    # 3. Gemini 校對
    proofread_srt_path = None
    proofread_status = False
    if PROOFREAD_AVAILABLE and whisper_result.get("srt"):
        try:
            base = os.path.splitext(whisper_result["srt"])[0]
            proofread_srt_path = f"{base}_proofread.srt"
            
            # 檢查是否已經有校對結果
            if os.path.exists(proofread_srt_path):
                logger.info(f"發現已完成的 Gemini 校對結果，跳過校對: {proofread_srt_path}")
                proofread_status = True
            else:
                logger.info("正在進行 Gemini 校對...")
                
                # 自動偵測多個講義 PDF
                final_pdf_paths = [lecture_pdf_pl] if lecture_pdf_pl and os.path.exists(lecture_pdf_pl) else []
                if not final_pdf_paths:
                    series_dir = os.path.dirname(episode_dir)
                    pdfs = glob.glob(os.path.join(series_dir, "*.pdf"))
                    if pdfs:
                        final_pdf_paths = sorted(pdfs)
                        logger.info(f"自動偵測到 {len(final_pdf_paths)} 個講義 PDF: {final_pdf_paths}")
                
                with api_semaphore:
                    lecture_text = load_lecture_text(pdf_path=final_pdf_paths)
                    # Pass proofread_prompt from playlist config down to the proofread engine
                    corrected = proofread_srt(whisper_result["srt"], lecture_text, custom_prompt=proofread_prompt_pl)
                if corrected:
                    with open(proofread_srt_path, "w", encoding="utf-8") as f:
                        f.write(build_srt(corrected))
                    logger.info(f"Gemini 校對完成: {proofread_srt_path}")
                    proofread_status = True
                    actually_did_work = True
        except Exception as e:
            logger.error(f"Gemini 校對失敗 (不影響主流程): {e}")
    else:
        logger.warning("校對模組未載入，跳過校對步驟")

    # 3.5 產生報表 (Excel, Docx) — use shared helper for naming consistency
    doc_prefix = _build_doc_prefix(safe_title, video_id)
        
    expected_xlsx = os.path.join(episode_dir, f"{safe_title}__{video_id}.xlsx")
    expected_docx_student = os.path.join(episode_dir, f"{doc_prefix}給學員校對.docx")
    expected_docx_ai = os.path.join(episode_dir, f"{doc_prefix}校對文本.docx")

    # 預期的舊檔名 (Legacy) -> 也就是 "T097V001" 類似的前綴
    match = re.search(r'(\d+)\s*$', title)
    if match:
        episode_num = str(int(match.group(1))).zfill(3)
    else:
        episode_num = title.strip().replace(' ', '_')
    legacy_base = f"{prefix}{episode_num}"
    
    legacy_xlsx = os.path.join(episode_dir, f"{legacy_base}.xlsx")
    legacy_docx_student = os.path.join(episode_dir, f"{legacy_base}給學員校對.docx")
    legacy_docx_ai = os.path.join(episode_dir, f"{legacy_base}校對文本.docx")
    
    has_xlsx = os.path.exists(expected_xlsx) or os.path.exists(legacy_xlsx)
    has_docx_student = os.path.exists(expected_docx_student) or os.path.exists(legacy_docx_student)
    has_docx_ai = os.path.exists(expected_docx_ai) or os.path.exists(legacy_docx_ai)

    reports_exist = has_xlsx and has_docx_student and has_docx_ai

    # 根據存在的檔案來設定路徑，供後續發送 Email 使用
    excel_path = expected_xlsx if os.path.exists(expected_xlsx) else legacy_xlsx
    docx_student = expected_docx_student if os.path.exists(expected_docx_student) else legacy_docx_student
    docx_ai = expected_docx_ai if os.path.exists(expected_docx_ai) else legacy_docx_ai

    if whisper_result.get("srt"):
        if reports_exist:
            logger.info("發現報表 (Excel, Docx) 已存在，跳過生成")
        else:
            try:
                import auto_postprocess
                logger.info("正在產生 Excel 與 Docx 報表...")
                base_name = os.path.splitext(os.path.basename(whisper_result["srt"]))[0]
                res = auto_postprocess.generate_excel_and_docx(episode_dir, base_name)
                if res:
                    excel_path, docx_student, docx_ai = res
                    actually_did_work = True
            except ImportError:
                logger.warning("找不到 auto_postprocess 模組，跳過報表生成")
            except Exception as e:
                logger.error(f"報表生成失敗: {e}")

    # 4. 讀取辨識結果摘要
    txt_preview = ""
    if whisper_result.get("txt") and os.path.exists(whisper_result["txt"]):
        with open(whisper_result["txt"], "r", encoding="utf-8") as f:
            content = f.read()
            txt_preview = content[:500] + ("..." if len(content) > 500 else "")

    # 5. 發送 Email 通知
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"【YouTube 影片辨識完成】{title}"
    body = (
        f"YouTube 影片語音辨識已完成\n"
        f"{'='*50}\n\n"
        f"影片標題: {title}\n"
        f"影片 ID: {video_id}\n"
        f"影片連結: https://www.youtube.com/watch?v={video_id}\n"
        f"完成時間: {now}\n"
        f"使用模型: Whisper {WHISPER_MODEL}\n"
        f"輸出目錄: {episode_dir}\n"
        f"校對完成: {'YES - ' + os.path.basename(proofread_srt_path) if proofread_srt_path else 'NO'}\n\n"
        f"辨識結果預覽:\n"
        f"{'-'*50}\n"
        f"{txt_preview}\n"
        f"{'-'*50}\n\n"
        f"附件說明:\n"
        f"  - *_proofread.srt: Gemini 校對後字幕\n"
        f"  - *.srt: Whisper 原始輸出\n"
        f"  - *.xlsx: 雙邊對齊工作底稿\n"
        f"  - *給學員校對.docx: 學員手動加標點用\n"
        f"  - *校對文本.docx: 餵給 AI 加標點用\n\n"
        f"此為系統自動發送通知。"
    )

    attachments = []
    if proofread_srt_path and os.path.exists(proofread_srt_path):
        attachments.append(proofread_srt_path)  # 校對後的優先
    if whisper_result.get("srt"):
        attachments.append(whisper_result["srt"])  # 附上原始版供參考
    if excel_path and os.path.exists(excel_path):
        attachments.append(excel_path)
    if docx_student and os.path.exists(docx_student):
        attachments.append(docx_student)
    if docx_ai and os.path.exists(docx_ai):
        attachments.append(docx_ai)

    if actually_did_work:
        send_email(subject, body, attachments)
    else:
        logger.info(f"所有步驟均為跳過（已存在），不重複發送 Email: {title}")

    # WAV 音訊檔保留在該集資料夾中，不刪除
    logger.info(f"處理完成: {title} -> {episode_dir}")
    return {
        "success": True,
        "srt": whisper_result.get("srt"),
        "txt": whisper_result.get("txt"),
        "proofread": proofread_status,
        "episode_dir": episode_dir,
    }


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 播放清單自動追蹤 + Whisper 辨識"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅列出新影片，不進行下載和辨識",
    )
    args = parser.parse_args()

    # Dry run 模式不需要 GPU 鎖
    lock_fd = None

    try:
        logger.info("=" * 60)
        logger.info("YouTube 播放清單自動追蹤腳本啟動")
        logger.info(f"模式: {'DRY RUN' if args.dry_run else '正常執行'}")
        logger.info("=" * 60)

        # 取得啟用的播放清單 (只取狀態為 running 的清單)
        pm = PlaylistManager(config_file=CONFIG_FILE)
        enabled_playlists = pm.get_runnable_playlists()
        
        if not enabled_playlists:
            logger.warning("沒有需執行的播放清單 (可能全部暫停中或皆未啟用)，結束執行。")
            return

        while True:
            overall_success = 0
            overall_fail = 0
            
            # === GPU 互斥鎖：確保不會與 auto_meeting_process 同時使用 GPU ===
            if not args.dry_run:
                lock_fd = acquire_gpu_lock()
                if lock_fd is None:
                    logger.info("GPU 被其他行程佔用中，本輪跳過，10 秒後重試...")
                    time.sleep(10)
                    continue

            # 重新整理清單
            pm = PlaylistManager(config_file=CONFIG_FILE)
            enabled_playlists = pm.get_runnable_playlists()
            
            if not enabled_playlists:
                logger.warning("沒有需執行的播放清單 (可能全部暫停中或皆未啟用)，將在 10 分鐘後重試。")
            else:
                for pl in enabled_playlists:
                    global PLAYLIST_URL, NAS_OUTPUT_BASE
                    PLAYLIST_URL = pl.get("url", "")
                    # 強制使用全局基礎路徑，忽略個別清單的 output_dir 以符合「路徑固定」規則
                    NAS_OUTPUT_BASE = config_data.get("nas_output_base", "/mnt/nas/Whisper_auto_rum/")
                    playlist_name = pl.get("name", "Unknown")

                    # 初始化目錄與讀取狀態
                    setup_directories()
                    processed = load_processed_videos()
                    
                    # 取得播放清單影片
                    is_tracking_enabled = pl.get("track", True)
                    if not PLAYLIST_URL:
                        logger.info(f"清單 {playlist_name} 沒有 URL，從本地記錄載入虛擬清單")
                        all_videos = []
                        for vid, info in processed.items():
                            if pl["id"] == "__legacy__" and (not info.get("playlist_id") or info.get("playlist_id") == "__legacy__"):
                                all_videos.append({"id": vid, "title": info.get("title", f"Unknown_{vid}"), "url": ""})
                            elif info.get("playlist_id") == pl["id"]:
                                all_videos.append({"id": vid, "title": info.get("title", f"Unknown_{vid}"), "url": ""})
                    elif not is_tracking_enabled:
                        logger.info(f"清單 {playlist_name} 已停用追蹤 (track=False)，從本地記錄載入影片清單")
                        all_videos = []
                        # 從已處理的記錄中找出屬於這個清單的影片，以便進行重試或補漏
                        for vid, info in processed.items():
                            if info.get("playlist_id") == pl["id"]:
                                all_videos.append({"id": vid, "title": info.get("title", f"Unknown_{vid}"), "url": f"https://www.youtube.com/watch?v={vid}"})
                        # 如果是 legacy 且沒標記 playlist_id 的也算進去
                        if pl["id"] == "__legacy__":
                           for vid, info in processed.items():
                               if not info.get("playlist_id"):
                                   all_videos.append({"id": vid, "title": info.get("title", f"Unknown_{vid}"), "url": f"https://www.youtube.com/watch?v={vid}"})
                    else:
                        all_videos = get_playlist_videos()

                    if not all_videos:
                        logger.warning(f"無法從 {playlist_name} 取得影片資訊。")
                        continue

                    # 找出新影片
                    prefix = pl.get("folder_prefix", "T097V")
                    new_videos = find_new_videos(all_videos, processed, pl.get("id", ""), prefix=prefix, output_base=NAS_OUTPUT_BASE)
                    if not new_videos:
                        logger.info(f"清單 {playlist_name} 沒有需要處理的新影片。")
                        # Update processed_count for UI completeness
                        if "processed_count" not in pl or pl["processed_count"] != len(all_videos):
                            pm.update_playlist(pl["id"], {"processed_count": len(all_videos), "total_videos": len(all_videos)})
                        continue
                        
                    # 套用 batch_size 限制進行 Round-Robin 調度
                    batch_size = pl.get("batch_size", 5)
                    new_videos_batch = new_videos[:batch_size]
                    
                    logger.info(f"清單 {playlist_name} 共有 {len(new_videos)} 期待處理，本輪將處理前 {len(new_videos_batch)} 集")
                    
                    # 預先更新總數
                    pm.update_playlist(pl["id"], {"total_videos": len(all_videos)})

                    # Dry run 模式
                    if args.dry_run:
                        logger.info(f"\n[DRY RUN] {playlist_name} 將會處理以下影片:")
                        for i, v in enumerate(new_videos_batch, 1):
                            logger.info(f"  {i}. [{v['id']}] {v['title']}")
                        continue

                    # 處理新影片
                    success_count = 0
                    fail_count = 0

                    # 使用 ThreadPoolExecutor 並行處理多部影片
                    max_workers = min(len(new_videos_batch), batch_size)
                    logger.info(f"啟動 {max_workers} 個工作執行緒並行處理...")
                    
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # 提交所有任務
                        future_to_video = {executor.submit(process_video, video, pl): video for video in new_videos_batch}
                        
                        for future in concurrent.futures.as_completed(future_to_video):
                            video = future_to_video[future]
                            try:
                                result = future.result()
                                if result["success"]:
                                    success_count += 1
                                    # 執行緒安全地更新狀態
                                    with state_lock:
                                        # 重新讀取，以免其他執行緒剛存過
                                        current_processed = load_processed_videos()
                                        current_processed[video["id"]] = {
                                            "title": video["title"],
                                            "processed_at": datetime.now().isoformat(),
                                            "srt": result.get("srt", ""),
                                            "txt": result.get("txt", ""),
                                            "proofread": result.get("proofread", False),
                                            "playlist_id": pl.get("id", ""),
                                        }
                                        save_processed_videos(current_processed)
                                else:
                                    fail_count += 1
                                    logger.error(f"處理失敗: {video['title']} - {result.get('error', '未知錯誤')}")
                            except Exception as exc:
                                fail_count += 1
                                logger.error(f"影片處理過程中發生未預期錯誤: {video['title']} - {exc}")
                    
                    overall_success += success_count
                    overall_fail += fail_count
                    logger.info(f"清單 {playlist_name} 執行完畢 (本輪成功: {success_count}, 失敗: {fail_count})")
                    
                    # 更新處理數量
                    pm._config = pm._load_config() # Reload in case of concurrent changes
                    current_processed_total = len([v for v in load_processed_videos().values() if v.get("playlist_id") == pl["id"]])
                    pm.update_playlist(pl["id"], {"processed_count": current_processed_total})

            # === 釋放 GPU 鎖：讓其他行程（如月會聽打）有機會在等待期間使用 GPU ===
            if lock_fd:
                # 只有在真正拿到鎖的情況下才釋放，並清空模型快取以節省 VRAM
                global _whisper_model_cache
                _whisper_model_cache.clear()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                release_gpu_lock(lock_fd)
                lock_fd = None

            # 總結一輪
            logger.info("=" * 60)
            logger.info(f"本輪執行完成 - 總成功: {overall_success}, 總失敗: {overall_fail}")
            logger.info("正在等待下一輪 (10 分鐘)...")
            logger.info("=" * 60)
            
            if args.dry_run:
                break # Dry run mode runs only once
                
            time.sleep(600)  # Sleep for 10 minutes

    finally:
        # 不管正常結束、例外或崩潰還原，都確保 GPU 鎖被釋放
        if lock_fd:
            release_gpu_lock(lock_fd)


if __name__ == "__main__":
    main()

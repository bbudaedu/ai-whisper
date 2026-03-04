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

import os
import sys
import re
import json
import subprocess
import smtplib
import logging
import argparse
import glob
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import fcntl

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

# yt-dlp 設定
YTDLP_BIN = "/usr/local/bin/yt-dlp"
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
LOG_FILE = os.path.join(BASE_DIR, "auto_youtube_whisper.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,  # Ensure handlers are applied even if root logger was pre-configured
)
logger = logging.getLogger(__name__)


def setup_directories():
    """建立所需目錄"""
    os.makedirs(NAS_OUTPUT_BASE, exist_ok=True)


def get_episode_dir(title):
    """從影片標題提取集數，建立對應資料夾路徑
    例如: '佛教公案選集 簡豐文居士 011' -> '/mnt/nas/Whisper_auto_rum/T097V/T097V011'
    """
    # 從標題末尾提取數字
    match = re.search(r'(\d+)\s*$', title)
    if match:
        episode_num = str(int(match.group(1))).zfill(3)  # 補足三位數: '1' -> '001'
    else:
        # 無法提取集數，使用全標題
        episode_num = title.strip().replace(' ', '_')

    episode_dir = os.path.join(NAS_OUTPUT_BASE, f"T097V{episode_num}")
    os.makedirs(episode_dir, exist_ok=True)
    logger.info(f"輸出目錄: {episode_dir}")
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


def check_video_files_exist(title, video_id):
    """檢查預期的輸出檔案是否已經存在"""
    # 取得預期目錄
    match = re.search(r'(\d+)\s*$', title)
    if match:
        episode_num = str(int(match.group(1))).zfill(3)
    else:
        episode_num = title.strip().replace(' ', '_')
    episode_dir = os.path.join(NAS_OUTPUT_BASE, f"T097V{episode_num}")
    
    # 取得安全檔名
    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
    ).strip()
    if not safe_title:
        safe_title = video_id
        
    expected_txt = os.path.join(episode_dir, f"{safe_title}__{video_id}.txt")
    expected_srt = os.path.join(episode_dir, f"{safe_title}__{video_id}.srt")
    expected_proofread = os.path.join(episode_dir, f"{safe_title}__{video_id}_proofread.srt")
    
    # 向後相容：舊版純檔名 (例如 T097V001.txt)
    old_txt = os.path.join(episode_dir, f"T097V{episode_num}.txt")
    old_srt = os.path.join(episode_dir, f"T097V{episode_num}.srt")
    
    # 強力標準：必須同時完成 Whisper (txt) 與 Gemini 校對 (proofread.srt)
    # 或者存在舊版手動完成的 srt 與 txt
    if (os.path.exists(expected_proofread) and os.path.exists(expected_txt)) or \
       (os.path.exists(old_srt) and os.path.exists(old_txt)):
        return True
    return False

def find_new_videos(all_videos, processed):
    """找出尚未處理的新影片，並加上雙重防呆：檢查實體檔案是否存在"""
    new_videos = []
    missing_in_json_but_done = []
    
    for v in all_videos:
        video_id = v["id"]
        title = v["title"]
        
        # 1. 檢查 JSON 狀態檔
        if video_id in processed:
            continue
            
        # 2. 檢查 NAS 目錄是否有實體檔案存在
        if check_video_files_exist(title, video_id):
            logger.info(f"警告: [{video_id}] {title} 檔案已存在，但未記錄在進度檔中，強制跳過並補回。")
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
                "txt": "recovered from disk"
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


def run_whisper(audio_path, episode_dir):
    """使用 Whisper large-v2 進行語音辨識"""
    basename = os.path.splitext(os.path.basename(audio_path))[0]
    
    # 檢查是否已經有辨識結果
    srt_path = os.path.join(episode_dir, f"{basename}.srt")
    txt_path = os.path.join(episode_dir, f"{basename}.txt")
    if os.path.exists(srt_path) and os.path.exists(txt_path):
        logger.info(f"發現已完成的 Whisper 辨識結果，跳過辨識: {srt_path}")
        return {"srt": srt_path, "txt": txt_path, "basename": basename}

    logger.info(f"正在執行 Whisper 辨識: {basename}")

    cmd = [
        WHISPER_BIN, audio_path,
        "--model", WHISPER_MODEL,
        "--language", WHISPER_LANG,
        "--initial_prompt", WHISPER_PROMPT,
        "--output_dir", episode_dir,
        "--output_format", "all",   # 輸出 txt, srt, vtt, json, tsv
    ]

    try:
        # Redirect whisper stdout/stderr to log file to keep cron log clean
        with open(LOG_FILE, "a", encoding="utf-8") as log_fh:
            subprocess.run(cmd, check=True, timeout=7200, stdout=log_fh, stderr=log_fh)
    except subprocess.TimeoutExpired:
        logger.error(f"Whisper 辨識逾時 (7200秒): {basename}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Whisper 辨識失敗: {e}")
        return None

    # 檢查輸出檔案
    srt_path = os.path.join(episode_dir, f"{basename}.srt")
    txt_path = os.path.join(episode_dir, f"{basename}.txt")

    if os.path.exists(srt_path) and os.path.exists(txt_path):
        logger.info(f"辨識完成: {srt_path}")
        return {"srt": srt_path, "txt": txt_path, "basename": basename}
    else:
        logger.error(f"辨識完成但找不到輸出檔案")
        # 嘗試找到任何輸出
        found_srt = glob.glob(os.path.join(episode_dir, f"{basename}.srt"))
        found_txt = glob.glob(os.path.join(episode_dir, f"{basename}.txt"))
        if found_srt or found_txt:
            return {
                "srt": found_srt[0] if found_srt else None,
                "txt": found_txt[0] if found_txt else None,
                "basename": basename,
            }
        return None


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
                        f"attachment; filename= {filename}",
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


def process_video(video):
    """處理單一影片: 下載 -> Whisper 辨識 -> Email 通知"""
    video_id = video["id"]
    title = video["title"]

    logger.info(f"{'='*60}")
    logger.info(f"開始處理: [{video_id}] {title}")
    logger.info(f"{'='*60}")

    # 0. 建立該集的輸出資料夾 (例: /mnt/nas/Whisper_auto_rum/T097V/T097V11)
    episode_dir = get_episode_dir(title)

    # 1. 下載音訊到該集資料夾
    audio_path = download_audio(video, episode_dir)
    if not audio_path:
        return {"success": False, "error": "下載失敗"}

    # 2. Whisper 辨識，輸出到該集資料夾
    whisper_result = run_whisper(audio_path, episode_dir)
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
                logger.info("正在进行 Gemini 校對...")
                lecture_text = load_lecture_text()
                corrected = proofread_srt(whisper_result["srt"], lecture_text)
                if corrected:
                    with open(proofread_srt_path, "w", encoding="utf-8") as f:
                        f.write(build_srt(corrected))
                    logger.info(f"Gemini 校對完成: {proofread_srt_path}")
                    proofread_status = True
        except Exception as e:
            logger.error(f"Gemini 校對失敗 (不影響主流程): {e}")
    else:
        logger.warning("校對模組未載入，跳過校對步驟")

    # 3.5 產生報表 (Excel, Docx)
    excel_path, docx_student, docx_ai = None, None, None
    if whisper_result.get("srt"):
        try:
            import auto_postprocess
            logger.info("正在產生 Excel 與 Docx 報表...")
            base_name = os.path.splitext(os.path.basename(whisper_result["srt"]))[0]
            res = auto_postprocess.generate_excel_and_docx(episode_dir, base_name)
            if res:
                excel_path, docx_student, docx_ai = res
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

    send_email(subject, body, attachments)

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

    # 確保不會有多個 Cron Job 同時執行造成重複處理
    lock_file_path = os.path.join(BASE_DIR, "auto_youtube_whisper.lock")
    try:
        lock_fd = open(lock_file_path, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, IOError):
        # fcntl.LOCK_NB 在無法取得 lock 時會丟出 BlockingIOError 或 IOError
        print("另一個 auto_youtube_whisper.py 行程正在執行中，本次跳過以避免重複處理。")
        return

    logger.info("=" * 60)
    logger.info("YouTube 播放清單自動追蹤腳本啟動")
    logger.info(f"模式: {'DRY RUN' if args.dry_run else '正常執行'}")
    logger.info("=" * 60)

    # 取得啟用的播放清單
    pm = PlaylistManager(config_file=CONFIG_FILE)
    enabled_playlists = pm.get_enabled_playlists()
    
    if not enabled_playlists:
        logger.warning("沒有啟用的播放清單，結束執行。")
        return

    overall_success = 0
    overall_fail = 0

    for pl in enabled_playlists:
        global PLAYLIST_URL, NAS_OUTPUT_BASE, WHISPER_MODEL
        PLAYLIST_URL = pl.get("url", "")
        NAS_OUTPUT_BASE = pl.get("output_dir", "") or config_data.get("nas_output_base", "/mnt/nas/Whisper_auto_rum/T097V")
        WHISPER_MODEL = pl.get("whisper_model", "large-v3")
        playlist_name = pl.get("name", "Unknown")

        if not PLAYLIST_URL:
            logger.warning(f"跳過清單 {playlist_name}因為沒有設定 URL")
            continue

        logger.info("-" * 60)
        logger.info(f"處理播放清單: {playlist_name} ({PLAYLIST_URL})")
        logger.info(f"輸出目錄: {NAS_OUTPUT_BASE}, 模型: {WHISPER_MODEL}")
        logger.info("-" * 60)

        # 初始化目錄與讀取狀態
        setup_directories()
        processed = load_processed_videos()
        
        # 取得播放清單影片
        all_videos = get_playlist_videos()
        if not all_videos:
            logger.warning(f"無法從 {playlist_name} 取得影片資訊。")
            continue

        # 找出新影片
        new_videos = find_new_videos(all_videos, processed)
        if not new_videos:
            logger.info(f"清單 {playlist_name} 沒有需要處理的新影片。")
            continue

        # Dry run 模式
        if args.dry_run:
            logger.info(f"\n[DRY RUN] {playlist_name} 將會處理以下影片:")
            for i, v in enumerate(new_videos, 1):
                logger.info(f"  {i}. [{v['id']}] {v['title']}")
            continue

        # 處理新影片
        success_count = 0
        fail_count = 0

        for video in new_videos:
            result = process_video(video)

            if result["success"]:
                # 記錄為已處理 (含 playlist_id 供 Dashboard 分群)
                processed[video["id"]] = {
                    "title": video["title"],
                    "processed_at": datetime.now().isoformat(),
                    "srt": result.get("srt", ""),
                    "txt": result.get("txt", ""),
                    "proofread": result.get("proofread", False),
                    "playlist_id": pl.get("id", ""),
                }
                save_processed_videos(processed)
                success_count += 1
            else:
                fail_count += 1
                logger.error(f"處理失敗: {video['title']} - {result.get('error', '未知錯誤')}")
        
        overall_success += success_count
        overall_fail += fail_count
        logger.info(f"清單 {playlist_name} 執行完畢 (成功: {success_count}, 失敗: {fail_count})")

    # 總結
    logger.info("=" * 60)
    logger.info(f"全部執行完成 - 總成功: {overall_success}, 總失敗: {overall_fail}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

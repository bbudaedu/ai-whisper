#!/usr/bin/env python3
"""
Whisper SRT 校對腳本 - 使用 Gemini 3 Pro Low (via 中轉 API)
=============================================================
讀取 Whisper 輸出的 .srt 檔案，搭配佛教公案講義，
透過 gemini-3-pro-low 進行字幕校對，輸出 _proofread.srt

用法:
    python auto_proofread.py <srt_file>
    python auto_proofread.py /mnt/nas/Whisper_auto_rum/T097V/T097V11/xxx.srt
"""

import os
import sys
import re
import json
import time
import logging
import argparse

from pipeline.api_client import ResilientAPIClient

# ================= 設定區域 =================

# 中轉 API 設定

# 載入設定檔 (config.json)
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
config_data = {}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"無法讀取 config.json: {e}")

API_BASE_URL = config_data.get("api_base_url", "http://192.168.100.201:8045/v1/chat/completions")
API_KEY = config_data.get("api_key", "sk-8f3999c2452d4124835ffaff469e22af")
PROOFREAD_MODEL = config_data.get("proofread_model", "gemini-3-flash")
LECTURE_PDF = config_data.get("lecture_pdf", "/mnt/nas/Whisper_auto_rum/T097V/CH857-03-01-001.pdf")

# 講義文字快取路徑
LECTURE_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lecture_cache.txt")

# 每次送出批次的字幕行數（控制 token 用量）
CHUNK_SIZE = config_data.get("proofread_chunk_size", 100)  # 預設 100 條

# ==========================================

# 設定日誌
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_proofread.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def extract_pdf_text(pdf_path):
    """從 PDF 提取文字，使用 pdfplumber"""
    try:
        import pdfplumber
        logger.info(f"正在擷取講義文字: {pdf_path}")
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        logger.info(f"講義共 {len(text)} 字元, 約 {len(text)//4} tokens")
        return text
    except ImportError:
        logger.warning("pdfplumber 未安裝，跳過講義讀取")
        return ""
    except Exception as e:
        logger.error(f"讀取 PDF 失敗: {e}")
        return ""


def load_lecture_text():
    """載入講義文字（使用快取避免重複解析 PDF）"""
    # 如果有快取且 PDF 沒更新，直接用快取
    if os.path.exists(LECTURE_CACHE):
        cache_mtime = os.path.getmtime(LECTURE_CACHE)
        pdf_mtime = os.path.getmtime(LECTURE_PDF) if os.path.exists(LECTURE_PDF) else 0
        if cache_mtime > pdf_mtime:
            logger.info(f"使用講義快取: {LECTURE_CACHE}")
            with open(LECTURE_CACHE, "r", encoding="utf-8") as f:
                return f.read()

    # 重新解析 PDF
    text = extract_pdf_text(LECTURE_PDF)
    if text:
        with open(LECTURE_CACHE, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"已更新講義快取: {LECTURE_CACHE}")
    return text


def parse_srt(srt_path):
    """解析 SRT 檔案，返回字幕列表"""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")
    subtitles = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            idx = lines[0].strip()
            timestamp = lines[1].strip()
            text = "\n".join(lines[2:]).strip()
            subtitles.append({"idx": idx, "timestamp": timestamp, "text": text})
    logger.info(f"共解析 {len(subtitles)} 條字幕")
    return subtitles


def build_srt(subtitles):
    """將字幕列表轉回 SRT 格式"""
    blocks = []
    for sub in subtitles:
        blocks.append(f"{sub['idx']}\n{sub['timestamp']}\n{sub['text']}")
    return "\n\n".join(blocks) + "\n"


# 建立統一 API 客戶端（含指數退避 + Circuit Breaker）
_api_client = ResilientAPIClient(
    api_base_url=API_BASE_URL,
    api_key=API_KEY,
    model=PROOFREAD_MODEL,
)


def call_api(prompt, max_retries=3):
    """呼叫中轉 API（透過 ResilientAPIClient）"""
    return _api_client.call(prompt)


def proofread_chunk(chunk_subtitles, lecture_text, chunk_num, total_chunks):
    """校對一個字幕批次"""
    logger.info(f"正在校對批次 {chunk_num}/{total_chunks} ({len(chunk_subtitles)} 條字幕)")

    # 組合字幕文本（只送文字，不送 timestamp，校對完再組回去）
    srt_text_only = ""
    for sub in chunk_subtitles:
        srt_text_only += f"[{sub['idx']}] {sub['text']}\n"

    # 建立 prompt
    lecture_section = ""
    if lecture_text:
        lecture_section = f"""
以下是上課講義內容（供你參考佛學詞彙正確用字）：
<講義>
{lecture_text[:3000]}
...（講義節錄，僅供參考詞彙校對）
</講義>

"""

    prompt = f"""你是一個佛學大師，精通經律論三藏十二部經典，以下文本是whisper產生的字幕文本，關於佛教公案選集的內容，有很多同音字聽打錯誤，幫我依據我提供的上課講義校對文本，嚴格依照以下規則，直接修正錯誤
1.這是講座字幕的文本，依照原本的用字遣詞斷句輸出，重複內容不能省略，不然字幕會出錯混亂
2.不要加標點符號
3.輸出繁體中文
{lecture_section}
以下是需要校對的字幕文本，格式是 [序號] 文字：
<字幕>
{srt_text_only}
</字幕>

請直接輸出校對後的結果，格式完全相同（[序號] 校對後文字），不要有任何說明或額外文字。"""

    result = call_api(prompt)
    if not result:
        logger.error(f"批次 {chunk_num} 校對失敗，中斷處理以保存進度")
        raise RuntimeError(f"API 請求失敗，中斷在批次 {chunk_num}")

    # 解析返回結果，更新字幕文字
    corrected_subtitles = list(chunk_subtitles)  # 複製一份
    lines = result.strip().split("\n")
    for line in lines:
        line = line.strip()
        match = re.match(r'^\[(\d+)\]\s*(.*)', line)
        if match:
            idx = match.group(1)
            corrected_text = match.group(2).strip()
            # 找到對應字幕並更新
            for i, sub in enumerate(corrected_subtitles):
                if sub["idx"] == idx:
                    corrected_subtitles[i] = dict(sub)
                    corrected_subtitles[i]["text"] = corrected_text
                    break

    return corrected_subtitles


def proofread_srt(srt_path, lecture_text):
    """對整個 SRT 檔進行分批校對"""
    subtitles = parse_srt(srt_path)
    if not subtitles:
        logger.error("無法解析 SRT 檔案")
        return None

    # 設定 checkpoint 檔案路徑
    base = os.path.splitext(srt_path)[0]
    checkpoint_file = f"{base}_checkpoint.json"

    # 讀取已完成的進度
    completed_chunks = 0
    all_corrected = []
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
                completed_chunks = checkpoint_data.get("completed_chunks", 0)
                all_corrected = checkpoint_data.get("all_corrected", [])
                logger.info(f"發現中斷點進度，已完成 {completed_chunks} 個批次，恢復執行")
        except Exception as e:
            logger.warning(f"讀取 checkpoint 失敗: {e}，將重新開始")
            completed_chunks = 0
            all_corrected = []

    # 分批處理
    chunks = [subtitles[i:i+CHUNK_SIZE] for i in range(0, len(subtitles), CHUNK_SIZE)]
    total_chunks = len(chunks)
    logger.info(f"共 {len(subtitles)} 條字幕，分成 {total_chunks} 批處理 (每批 {CHUNK_SIZE} 條)")

    for i, chunk in enumerate(chunks, 1):
        if i <= completed_chunks:
            logger.info(f"跳過已完成的批次 {i}/{total_chunks}")
            continue

        corrected = proofread_chunk(chunk, lecture_text, i, total_chunks)
        all_corrected.extend(corrected)
        
        # 儲存進度
        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump({"completed_chunks": i, "all_corrected": all_corrected}, f, ensure_ascii=False, indent=2)
                logger.debug(f"已儲存批次 {i} 的進度")
        except Exception as e:
            logger.error(f"儲存 checkpoint 失敗: {e}")

        # 批次間稍作停頓，避免速率限制
        if i < total_chunks:
            time.sleep(2)

    # 處理完成，刪除 checkpoint
    if os.path.exists(checkpoint_file):
        try:
            os.remove(checkpoint_file)
            logger.info("校對全部完成，已清除 checkpoint 檔案")
        except Exception as e:
            logger.warning(f"清除 checkpoint 失敗: {e}")

    return all_corrected


def main():
    parser = argparse.ArgumentParser(description="Whisper SRT 校對 - Gemini Pro")
    parser.add_argument("srt_file", help="要校對的 .srt 檔案路徑")
    args = parser.parse_args()

    srt_path = args.srt_file
    if not os.path.exists(srt_path):
        logger.error(f"SRT 檔案不存在: {srt_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Whisper SRT 校對腳本啟動")
    logger.info(f"輸入: {srt_path}")
    logger.info(f"模型: {PROOFREAD_MODEL}")
    logger.info("=" * 60)

    # 1. 載入講義
    lecture_text = load_lecture_text()
    if not lecture_text:
        logger.warning("未能載入講義，將進行無講義校對")

    # 2. 校對
    try:
        corrected = proofread_srt(srt_path, lecture_text)
        if not corrected:
            logger.error("校對失敗")
            sys.exit(1)
    except RuntimeError as e:
        logger.error(f"腳本中斷: {e}")
        sys.exit(1)

    # 3. 輸出校對後的 SRT
    base = os.path.splitext(srt_path)[0]
    output_path = f"{base}_proofread.srt"
    srt_content = build_srt(corrected)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    logger.info(f"校對完成: {output_path}")
    return output_path


if __name__ == "__main__":
    main()

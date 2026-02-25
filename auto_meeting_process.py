import os
import time
import shutil
import subprocess
import smtplib
import logging
import torch
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from transformers import pipeline
from docx import Document

# ================= 設定區域 =================
# 監控與輸出路徑
WATCH_DIR = "/mnt/nas/Whisper_auto_rum/月會聽打"
PROCESSED_DIR = os.path.join(WATCH_DIR, "processed")
OUTPUT_DIR = os.path.join(WATCH_DIR, "output")
TEMP_DIR = os.path.join(WATCH_DIR, "temp_whisper")

# Email 設定
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "bbudaedu@gmail.com"
EMAIL_PASS = "khwvartcqbgztwgr"
EMAIL_TO = ["jackyfang@budaedu.org", "tyguo@budaedu.org", "zrwang@budaedu.org"]

# AI 模型設定
PUNCTUATION_MODEL = "oliverguhr/fullstop-punctuation-multilang-large"
WHISPER_MODEL = "large-v2"
WHISPER_LANG = "Chinese"
WHISPER_PROMPT = "會議記錄 "
# Whisper 執行檔絕對路徑 (請依實際情況調整，通常在 venv/bin 下)
WHISPER_BIN = "/home/budaedu/ai-whisper/venv/bin/whisper"

# ==========================================

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("meeting_process.log"),
        logging.StreamHandler()
    ]
)

def setup_directories():
    for d in [PROCESSED_DIR, OUTPUT_DIR, TEMP_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def send_email(subject, body, attachment_path):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = ", ".join(EMAIL_TO)
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    if attachment_path and os.path.exists(attachment_path):
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {filename}")
        msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        server.quit()
        logging.info(f"Email 已發送至 {EMAIL_TO}")
    except Exception as e:
        logging.error(f"Email 發送失敗: {e}")

def run_whisper(filepath):
    """呼叫系統 Whisper 指令進行轉錄"""
    logging.info(f"正在執行 Whisper 轉錄: {os.path.basename(filepath)}")
    
    cmd = [
        WHISPER_BIN, filepath,
        "--model", WHISPER_MODEL,
        "--language", WHISPER_LANG,
        "--initial_prompt", WHISPER_PROMPT,
        "--output_dir", TEMP_DIR,
        "--output_format", "txt"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        # Whisper 會產生同檔名的 .txt
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        txt_path = os.path.join(TEMP_DIR, base_name + ".txt")
        
        if os.path.exists(txt_path):
            return txt_path
        else:
            logging.error("Whisper 執行完成但找不到輸出的 txt 檔案")
            return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Whisper 執行失敗: {e}")
        return None
    except FileNotFoundError:
        logging.error(f"找不到 Whisper 執行檔，請檢查路徑: {WHISPER_BIN}")
        return None

def apply_punctuation(text, pipe):
    """使用模型修復標點符號"""
    logging.info("正在進行標點符號修復...")
    
    # 清理並切分文本
    text = text.replace("\n", "").replace("\r", "").replace(" ", "")
    max_chunk_chars = 250
    chunks = [text[i:i + max_chunk_chars] for i in range(0, len(text), max_chunk_chars)]

    full_punctuated_text = ""
    for chunk in chunks:
        result = pipe(chunk)
        for item in result:
            full_punctuated_text += item['word']
            tag = item['entity_group']
            if tag != 'O' and tag != '0':
                full_punctuated_text += tag

    # 格式化清理
    final = full_punctuated_text.replace("##", "")
    final = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', final)
    final = final.replace(",", "，").replace(".", "。").replace("?", "？").replace("!", "！").replace(":", "：")
    for punc in "，。？！：":
        final = final.replace(" " + punc, punc)
        
    return final

def create_docx(text, output_path):
    """將文字轉換為 DOCX"""
    doc = Document()
    doc.add_heading('會議記錄聽打結果', 0)
    
    # 簡單分段
    paragraphs = text.split("。")
    for p in paragraphs:
        if p.strip():
            doc.add_paragraph(p.strip() + "。")
            
    doc.save(output_path)
    logging.info(f"已建立 Word 檔: {output_path}")

def main():
    setup_directories()
    
    # 預先載入標點模型
    logging.info("正在載入標點模型...")
    device = 0 if torch.cuda.is_available() else -1
    punctuator = pipeline("token-classification", model=PUNCTUATION_MODEL, device=device, aggregation_strategy="simple")
    logging.info("系統啟動完成，開始監控...")

    while True:
        try:
            if not os.path.exists(WATCH_DIR):
                time.sleep(10); continue

            # 監控音檔 (mp3, wav, m4a)
            files = [f for f in os.listdir(WATCH_DIR) if f.lower().endswith(('.mp3', '.wav', '.m4a'))]
            
            for file in files:
                filepath = os.path.join(WATCH_DIR, file)
                # 簡單檢查檔案大小 > 0 代表寫入可能完成了
                if os.path.getsize(filepath) == 0: continue

                logging.info(f"發現音檔: {file}")
                
                # 1. 執行 Whisper
                txt_path = run_whisper(filepath)
                if not txt_path: continue

                # 2. 讀取轉錄文字
                with open(txt_path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()

                # 3. 執行標點修復
                final_text = apply_punctuation(raw_text, punctuator)

                # 4. 產生 DOCX
                base_name = os.path.splitext(file)[0]
                docx_filename = f"{base_name}_punctuated.docx"
                docx_path = os.path.join(OUTPUT_DIR, docx_filename)
                create_docx(final_text, docx_path)

                # 5. 發送 Email
                subject = f"【會議聽打完成】{file}"
                body = f"檔案 {file} 已完成轉錄與標點修復。\n\n請查收附件 Word 檔。\n\n系統自動發送"
                send_email(subject, body, docx_path)

                # 6. 清理與歸檔
                shutil.move(filepath, os.path.join(PROCESSED_DIR, file)) # 移動原始音檔
                os.remove(txt_path) # 刪除暫存 txt
                logging.info(f"任務完成: {file}")

            time.sleep(10)

        except Exception as e:
            logging.error(f"主迴圈錯誤: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()

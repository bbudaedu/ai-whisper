import os
import time
import shutil
import torch
import logging
from transformers import pipeline
import re

# --- 設定路徑 ---
WATCH_DIR = "/mnt/nas/Whisper_auto_rum/月會聽打"
PROCESSED_DIR = os.path.join(WATCH_DIR, "processed")  # 處理完的原始檔放這
OUTPUT_DIR = os.path.join(WATCH_DIR, "output")        # 加好標點的檔放這
MODEL_NAME = "oliverguhr/fullstop-punctuation-multilang-large"

# --- 設定日誌 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_punctuation.log"),
        logging.StreamHandler()
    ]
)

def setup_directories():
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def load_model():
    logging.info(f"正在加載模型: {MODEL_NAME} ...")
    device = 0 if torch.cuda.is_available() else -1
    try:
        pipe = pipeline("token-classification", model=MODEL_NAME, device=device, aggregation_strategy="simple")
        logging.info("模型加載成功！")
        return pipe
    except Exception as e:
        logging.error(f"模型加載失敗: {e}")
        return None

def process_file(filepath, punctuator):
    filename = os.path.basename(filepath)
    logging.info(f"發現新檔案，開始處理: {filename}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        # --- 核心切分邏輯 (保留您的原始邏輯) ---
        text_single_block = text.replace("\n", "").replace("\r", "").replace(" ", "")
        max_chunk_chars = 250
        chunks = [text_single_block[i:i + max_chunk_chars] for i in range(0, len(text_single_block), max_chunk_chars)]

        full_punctuated_text = ""
        for i, chunk in enumerate(chunks):
            result = punctuator(chunk)
            current_chunk_text = ""
            for item in result:
                current_chunk_text += item['word']
                tag = item['entity_group']
                if tag != 'O' and tag != '0':
                    current_chunk_text += tag
            full_punctuated_text += current_chunk_text

        # 格式化清理
        final_text = full_punctuated_text.replace("##", "")
        final_text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', final_text)
        final_text = final_text.replace(",", "，").replace(".", "。")
        final_text = final_text.replace("?", "？").replace("!", "！").replace(":", "：")
        for punc in "，。？！：":
            final_text = final_text.replace(" " + punc, punc)

        # 儲存結果
        output_filename = f"{os.path.splitext(filename)[0]}_punctuated.txt"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_text.strip())
        
        logging.info(f"處理完成，結果儲存至: {output_path}")

        # 移動原始檔案到 processed 資料夾 (避免重複處理)
        shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
        logging.info(f"原始檔案已歸檔至 processed 資料夾")

    except Exception as e:
        logging.error(f"處理檔案 {filename} 時發生錯誤: {e}")

def main():
    setup_directories()
    punctuator = load_model()
    
    if not punctuator:
        return

    logging.info(f"開始監控資料夾: {WATCH_DIR}")
    
    while True:
        try:
            # 檢查 NAS 是否掛載成功，如果路徑不存在就等待
            if not os.path.exists(WATCH_DIR):
                logging.warning(f"找不到監控路徑 {WATCH_DIR}，可能是 NAS 尚未掛載，10秒後重試...")
                time.sleep(10)
                continue

            # 掃描資料夾內的 .txt 檔案
            files = [f for f in os.listdir(WATCH_DIR) if f.endswith('.txt') and os.path.isfile(os.path.join(WATCH_DIR, f))]
            
            for file in files:
                filepath = os.path.join(WATCH_DIR, file)
                # 確保不是正在寫入的暫存檔 (簡單判斷：檔案大小大於0)
                if os.path.getsize(filepath) > 0:
                    process_file(filepath, punctuator)
            
            # 每 10 秒檢查一次
            time.sleep(10)
            
        except Exception as e:
            logging.error(f"監控迴圈發生錯誤: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()

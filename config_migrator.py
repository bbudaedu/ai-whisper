import json
import os

CONFIG_FILE = "config.json"

def migrate_config():
    if not os.path.exists(CONFIG_FILE):
        print("config.json 不存在，略過遷移")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    changed = False
    
    # 提取全域設定
    global_lang = config.get("whisper_lang", "")
    global_prompt = config.get("whisper_prompt", "")
    global_lecture = config.get("lecture_pdf", "")

    # 檢查每個播放清單
    for playlist in config.get("playlists", []):
        if "whisper_lang" not in playlist:
            # 莫哥禪法預設給 "auto" (因為有中緬雙語)
            if "莫哥禪法" in playlist.get("name", ""):
                playlist["whisper_lang"] = "auto"
                # 給一個雙語特化的 prompt
                playlist["whisper_prompt"] = "莫哥禪法 緬甸語與中文現場翻譯 佛教公案選集 不要標點符號"
            else:
                playlist["whisper_lang"] = global_lang
            changed = True
            
        if "whisper_prompt" not in playlist:
            if "莫哥禪法" not in playlist.get("name", ""):
                playlist["whisper_prompt"] = global_prompt
            changed = True
            
        if "lecture_pdf" not in playlist:
            playlist["lecture_pdf"] = global_lecture
            changed = True

    if changed:
        # 備份
        backup_file = CONFIG_FILE + ".bak"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # 覆寫
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
        print(f"成功將全域參數遷移至 playlists 中。原檔已備份至 {backup_file}")
    else:
        print("沒有需要遷移的播放清單。")

if __name__ == "__main__":
    migrate_config()

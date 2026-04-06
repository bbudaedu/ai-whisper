import json, os, glob

json_path = "/home/budaedu/ai-whisper/processed_videos.json"
with open(json_path, "r", encoding='utf-8') as f:
    data = json.load(f)

count = 0
for vid, info in data.items():
    if "佛教公案選集" in info.get("title", ""):
        # Check T097V root for these legacy ones
        import re
        match = re.search(r"(\d+)\s*$", info["title"])
        if match:
            ep = match.group(1).zfill(3)
            ep_dir = f"/mnt/nas/Whisper_auto_rum/T097V/T097V{ep}"
            if os.path.exists(ep_dir):
                proofread_files = glob.glob(os.path.join(ep_dir, "*_proofread.srt"))
                if proofread_files:
                    if not info.get("proofread"):
                        info["proofread"] = True
                        # Update paths if recovered
                        if info.get("srt") == "recovered from disk":
                           srt_files = glob.glob(os.path.join(ep_dir, "*.srt"))
                           actual_srt = [s for s in srt_files if "_proofread" not in s]
                           if actual_srt:
                               info["srt"] = actual_srt[0]
                           txt_files = glob.glob(os.path.join(ep_dir, "*.txt"))
                           if txt_files:
                               info["txt"] = txt_files[0]
                        count += 1

print(f"Updated {count} videos")
with open(json_path, "w", encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

import json

json_path = "/home/budaedu/ai-whisper/processed_videos.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

count = 0
for vid, info in data.items():
    if "莫哥禪法" in info.get("title", ""):
        info["playlist_id"] = "pl_1772509672607"
        count += 1
        
print(f"Updated {count} mogok videos with playlist_id")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

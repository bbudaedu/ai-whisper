import json
import os
import re
import glob

with open('processed_videos.json', 'r') as f:
    processed = json.load(f)

legacy_videos = []
nas_base = "/mnt/nas/Whisper_auto_rum/T097V"
for vid, info in processed.items():
    if not info.get("playlist_id"):
        info["video_id"] = vid
        legacy_videos.append(info)

for info in legacy_videos:
    title = info.get("title", "")
    match = re.search(r'(\d+)\s*$', title)
    if match:
        ep = str(int(match.group(1))).zfill(3)
        ep_dir = os.path.join(nas_base, f"T097V{ep}")
        if os.path.isdir(ep_dir):
            proofread_files = glob.glob(os.path.join(ep_dir, "*_proofread.srt"))
            if proofread_files:
                info["proofread"] = True

print("Whispered:", len(legacy_videos))
print("Proofread:", sum(1 for v in legacy_videos if v.get("proofread")))
print("Pending:", len(legacy_videos) - sum(1 for v in legacy_videos if v.get("proofread")))

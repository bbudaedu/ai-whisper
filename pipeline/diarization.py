import os
import torch
from pyannote.audio import Pipeline

# 載入模型 (需設定 HuggingFace Token 若有需要)
# 這裡預設使用 pyannote/speaker-diarization-3.1
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
)

def run_diarization(audio_path: str):
    """
    執行說話者分離
    回傳: [(start, end, speaker_label), ...]
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    diarization = pipeline(audio_path)

    results = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        results.append((turn.start, turn.end, speaker))

    return results

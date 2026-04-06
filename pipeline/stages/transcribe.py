"""Transcribe stage — 使用 faster-whisper 進行語音辨識。"""
import logging

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行轉錄 stage。"""
    from auto_youtube_whisper import run_whisper

    audio_path = context["audio_path"]
    episode_dir = context["episode_dir"]
    pl_config = context.get("playlist_config", {})

    whisper_model = pl_config.get("whisper_model", "large-v3")
    whisper_lang = pl_config.get("whisper_lang", "auto")
    whisper_prompt = pl_config.get("whisper_prompt", "")

    result = run_whisper(
        audio_path,
        episode_dir,
        whisper_model=whisper_model,
        whisper_lang=whisper_lang,
        whisper_prompt=whisper_prompt,
    )
    if result is None:
        raise RuntimeError(f"Whisper 辨識失敗: {audio_path}")

    logger.info(f"Transcribe stage 完成: srt={result['srt']}")
    return {
        "srt_path": result["srt"],
        "txt_path": result["txt"],
        "episode_dir": episode_dir,
    }

"""Download stage — 從 YouTube 下載音訊到集數目錄。"""
import logging
import os

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行下載 stage。"""
    from auto_youtube_whisper import download_audio, get_episode_dir

    audio_path = context.get("audio_path")
    episode_dir = context.get("episode_dir")
    if audio_path and episode_dir:
        if not os.path.exists(audio_path):
            raise RuntimeError(f"上傳檔案不存在: {audio_path}")
        logger.info(f"Download stage bypass: {audio_path}")
        return {"audio_path": audio_path, "episode_dir": episode_dir}

    video_id = context["video_id"]
    title = context["title"]
    pl_config = context.get("playlist_config", {})
    output_base = context.get("output_base")
    requester = context.get("requester")
    task_source = context.get("task_source")

    if output_base and task_source == "external":
        safe_requester = str(requester or "unknown").strip().replace("/", "_")
        episode_dir = os.path.join(output_base, safe_requester, str(stage_task.task_id))
        os.makedirs(episode_dir, exist_ok=True)
    else:
        prefix = pl_config.get("folder_prefix", "T097V")
        episode_dir = get_episode_dir(title, prefix=prefix, output_base=output_base)

    video = {"id": video_id, "title": title}

    audio_path = download_audio(video, episode_dir)
    if audio_path is None:
        raise RuntimeError(f"下載失敗: {title} ({video_id})")

    logger.info(f"Download stage 完成: {audio_path}")
    return {
        "audio_path": audio_path,
        "episode_dir": episode_dir,
    }

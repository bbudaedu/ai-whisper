"""Proofread stage — 使用 Gemini API 校對字幕。"""
import logging
import os

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行校對 stage。"""
    from auto_proofread import load_lecture_text, proofread_srt, build_srt

    srt_path = context["srt_path"]
    episode_dir = context["episode_dir"]
    pl_config = context.get("playlist_config", {})

    lecture_pdf = pl_config.get("lecture_pdf", "")
    custom_prompt = pl_config.get("proofread_prompt", "")

    import glob

    pdf_paths = [lecture_pdf] if lecture_pdf and os.path.exists(lecture_pdf) else []
    if not pdf_paths:
        series_dir = os.path.dirname(episode_dir)
        pdfs = glob.glob(os.path.join(series_dir, "*.pdf"))
        if pdfs:
            pdf_paths = sorted(pdfs)

    lecture_text = load_lecture_text(pdf_path=pdf_paths)

    corrected = proofread_srt(srt_path, lecture_text, custom_prompt=custom_prompt)
    if not corrected:
        raise RuntimeError(f"校對失敗: {srt_path}")

    base = os.path.splitext(srt_path)[0]
    proofread_path = f"{base}_proofread.srt"
    with open(proofread_path, "w", encoding="utf-8") as f:
        f.write(build_srt(corrected))

    logger.info(f"Proofread stage 完成: {proofread_path}")
    return {
        "proofread_srt_path": proofread_path,
        "srt_path": srt_path,
        "episode_dir": episode_dir,
    }

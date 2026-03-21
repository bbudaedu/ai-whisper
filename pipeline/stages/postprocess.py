"""Postprocess stage — 產生 Excel 與 Word 報表。"""
import logging
import os

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行後處理 stage。"""
    import auto_postprocess

    srt_path = context["srt_path"]
    episode_dir = context["episode_dir"]

    base_name = os.path.splitext(os.path.basename(srt_path))[0]
    result = auto_postprocess.generate_excel_and_docx(episode_dir, base_name)
    if not result:
        raise RuntimeError(f"報表生成失敗: {episode_dir}/{base_name}")

    excel_path, docx_student, docx_ai = result
    logger.info(f"Postprocess stage 完成: excel={excel_path}")
    return {
        "excel_path": excel_path,
        "docx_student_path": docx_student,
        "docx_ai_path": docx_ai,
        "episode_dir": episode_dir,
    }

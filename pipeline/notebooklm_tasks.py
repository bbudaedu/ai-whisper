"""
NotebookLM Task Definitions
============================
Defines the 5 output types (mind map, presentation, summary,
infographic-full, infographic-compact) with prompt templates
and result parsing logic.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from database.persistence import log_task_event, register_artifact
from pipeline.queue.database import get_session

logger = logging.getLogger(__name__)


class OutputType(str, Enum):
    """The 5 supported NotebookLM output types."""
    MINDMAP = "mindmap"
    PRESENTATION = "presentation"
    SUMMARY = "summary"
    FAQ = "faq"
    GLOSSARY = "glossary"
    STUDIO_AUDIO = "studio_audio"
    STUDIO_MINDMAP = "studio_mindmap"
    INFOGRAPHIC_FULL = "infographic_full"
    INFOGRAPHIC_COMPACT = "infographic_compact"

    @classmethod
    def from_str(cls, s: str) -> 'OutputType':
        try:
            return cls(s)
        except ValueError:
            raise ValueError(f"'{s}' is not a valid OutputType")


# Human-readable labels (繁體中文)
OUTPUT_LABELS: dict[OutputType, str] = {
    OutputType.MINDMAP: "心智圖",
    OutputType.PRESENTATION: "簡報",
    OutputType.SUMMARY: "影片摘要",
    OutputType.INFOGRAPHIC_FULL: "資訊圖表標準",
    OutputType.INFOGRAPHIC_COMPACT: "資訊圖表精簡",
    OutputType.FAQ: "常見問題",
    OutputType.GLOSSARY: "詞彙表",
    OutputType.STUDIO_AUDIO: "錄音概覽 (Studio)",
    OutputType.STUDIO_MINDMAP: "原生心智圖 (Studio)",
}

# File suffixes per output type
OUTPUT_SUFFIXES: dict[OutputType, str] = {
    OutputType.MINDMAP: "_mindmap.md",
    OutputType.PRESENTATION: "_presentation.md",
    OutputType.SUMMARY: "_summary.md",
    OutputType.INFOGRAPHIC_FULL: "_infographic_full.md",
    OutputType.INFOGRAPHIC_COMPACT: "_infographic_compact.md",
    OutputType.FAQ: "_faq.md",
    OutputType.GLOSSARY: "_glossary.md",
    OutputType.STUDIO_AUDIO: "_studio_audio.txt",
    OutputType.STUDIO_MINDMAP: "_studio_mindmap.txt",
}


def build_prompt(output_type: OutputType, title: str, text_excerpt: str) -> str:
    """Build the prompt for a specific output type.

    Args:
        output_type: Which output to generate.
        title: Episode title (e.g. '佛教公案選集017_簡豐文居士').
        text_excerpt: The proofread text content (first ~4000 chars to stay
                      within NotebookLM's input limits).

    Returns:
        The prompt string to send to NotebookLM.
    """
    # Truncate to avoid exceeding NotebookLM chat input limits
    max_chars = 4000
    truncated = text_excerpt[:max_chars]
    if len(text_excerpt) > max_chars:
        truncated += "\n\n...(content truncated)..."

    prompts: dict[OutputType, str] = {
        OutputType.MINDMAP: (
            f"請根據以下佛學講座「{title}」的校對文本，產生一個心智圖。\n"
            f"請使用 Mermaid mindmap 語法輸出，以便直接渲染。\n"
            f"要求：\n"
            f"- 中心主題為講座標題\n"
            f"- 第二層為主要概念/段落主題\n"
            f"- 第三層為細節要點\n"
            f"- 使用繁體中文\n\n"
            f"校對文本：\n{truncated}"
        ),
        OutputType.PRESENTATION: (
            f"請根據以下佛學講座「{title}」的校對文本，產生一份 Markdown 格式的簡報大綱。\n"
            f"要求：\n"
            f"- 每張投影片以 `---` 分隔\n"
            f"- 第一張為標題頁（講座名稱 + 講師）\n"
            f"- 中間為內容（每張 3-5 個重點，含引用原文）\n"
            f"- 最後一張為總結與心得\n"
            f"- 使用繁體中文\n\n"
            f"校對文本：\n{truncated}"
        ),
        OutputType.SUMMARY: (
            f"請根據以下佛學講座「{title}」的校對文本，撰寫一份結構化的影片摘要。\n"
            f"要求：\n"
            f"- 開頭一段式總覽（50-100字）\n"
            f"- 分段重點整理（每段附標題）\n"
            f"- 關鍵術語列表（含簡短解釋）\n"
            f"- 結語與核心啟示\n"
            f"- 使用繁體中文\n\n"
            f"校對文本：\n{truncated}"
        ),
        OutputType.INFOGRAPHIC_FULL: (
            f"請根據以下佛學講座「{title}」的校對文本，設計一份完整的資訊圖表內容。\n"
            f"要求：\n"
            f"- 以 Markdown 表格和列表呈現\n"
            f"- 包含：講座基本資訊、核心概念框架、論點流程圖（文字描述）、\n"
            f"  關鍵引用、相關經典出處\n"
            f"- 儘量詳盡完整\n"
            f"- 使用繁體中文\n\n"
            f"校對文本：\n{truncated}"
        ),
        OutputType.INFOGRAPHIC_COMPACT: (
            f"請根據以下佛學講座「{title}」的校對文本，設計一份精簡版的資訊圖表。\n"
            f"要求：\n"
            f"- 以 Markdown 表格和列表呈現\n"
            f"- 僅保留：講座主題、3-5 個核心要點、1-2 句精華引用\n"
            f"- 適合快速瀏覽，控制在一頁以內\n"
            f"- 使用繁體中文\n\n"
            f"校對文本：\n{truncated}"
        ),
        OutputType.FAQ: (
            f"請根據以下佛學講座「{title}」的校對文本，產生一份常見問題（FAQ）列表。\n"
            f"要求：\n"
            f"- 提出 5-10 個大眾可能感興趣的問題\n"
            f"- 提供簡明扼要的回答\n"
            f"- 使用繁體中文\n\n"
            f"校對文本：\n{truncated}"
        ),
        OutputType.GLOSSARY: (
            f"請根據以下佛學講座「{title}」的校對文本，產生一份專有名詞詞彙表。\n"
            f"要求：\n"
            f"- 挑選講座中出現的核心術語或佛學名相\n"
            f"- 提供簡短的解釋或定義\n"
            f"- 使用繁體中文\n\n"
            f"校對文本：\n{truncated}"
        ),
        OutputType.STUDIO_AUDIO: "N/A (Studio Output)",
        OutputType.STUDIO_MINDMAP: "N/A (Studio Output)",
    }

    return prompts[output_type]


def parse_response(output_type: OutputType, raw_answer: str) -> str:
    """Parse and clean the raw NotebookLM answer for a given output type.

    Extracts code blocks if present, strips unnecessary preamble, etc.

    Args:
        output_type: The output type that was requested.
        raw_answer: The raw text answer from NotebookLM.

    Returns:
        Cleaned markdown content ready to write to file.
    """
    if not raw_answer:
        return ""

    text = raw_answer.strip()

    # Strip the follow-up reminder appended by notebooklm-mcp
    reminder_marker = "EXTREMELY IMPORTANT: Is that ALL you need to know?"
    if reminder_marker in text:
        text = text[:text.index(reminder_marker)].strip()

    # For mindmap, extract the mermaid code block if embedded
    if output_type == OutputType.MINDMAP:
        mermaid_match = re.search(r"```mermaid\s*\n(.*?)```", text, re.DOTALL)
        if mermaid_match:
            mermaid_content = mermaid_match.group(1).strip()
            return f"```mermaid\n{mermaid_content}\n```"

    return text


def get_output_path(episode_dir: str, title: str, output_type: OutputType) -> str:
    """Compute the output file path for a given episode and output type.

    Files are stored in a 'notebooklm/' subdirectory within the episode dir.

    Args:
        episode_dir: Path to the episode directory (e.g. /mnt/nas/.../T097V017).
        title: Episode title used as filename prefix.
        output_type: The output type.

    Returns:
        Absolute path to the output file.
    """
    subdir = os.path.join(episode_dir, "notebooklm")
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title.strip())
    # Truncate title to keep path length reasonable
    safe_title = safe_title[:60]
    filename = f"{safe_title}{OUTPUT_SUFFIXES[output_type]}"
    return os.path.join(subdir, filename)


def save_output(filepath: str, content: str) -> None:
    """Write output content to a file, creating directories as needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    Path(filepath).write_text(content, encoding="utf-8")
    logger.info(f"Saved NotebookLM output: {filepath}")


def check_existing_outputs(episode_dir: str, title: str) -> dict[OutputType, bool]:
    """Check which output types already exist for an episode.

    Returns:
        Dict mapping each OutputType to whether its file exists.
    """
    result: dict[OutputType, bool] = {}
    for ot in OutputType:
        path = get_output_path(episode_dir, title, ot)
        result[ot] = os.path.isfile(path)
    return result


@dataclass
class TaskResult:
    """Result of a single NotebookLM task execution."""
    output_type: OutputType
    success: bool
    filepath: str = ""
    error: str = ""
    session_id: Optional[str] = None

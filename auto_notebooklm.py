"""
auto_notebooklm.py — NotebookLM 後製自動化主程式
=================================================
掃描 NAS 上已完成排版的 episodes，為每集建立 5 種產出任務，
並透過 Rate-limit scheduler 依序執行。

用法：
  python3 auto_notebooklm.py                  # 掃描全部 playlists 並處理
  python3 auto_notebooklm.py --episode T097V017  # 只處理單集
  python3 auto_notebooklm.py --status          # 顯示佇列狀態
"""

import argparse
import glob
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

from pipeline.notebooklm_client import NotebookLMClient
from pipeline.notebooklm_scheduler import NotebookLMScheduler
from pipeline.notebooklm_tasks import OutputType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [notebooklm] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
PROCESSED_FILE = os.path.join(BASE_DIR, "processed_videos.json")
QUEUE_FILE = os.path.join(BASE_DIR, "notebooklm_queue.json")


def load_config() -> dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_processed() -> dict[str, Any]:
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def resolve_episode_dir(
    config: dict[str, Any],
    processed: dict[str, Any],
    video_id: str,
) -> Optional[tuple[str, str, str]]:
    """Resolve (episode_dir, folder_prefix, title) for a video_id.

    Returns None if the episode directory or a report file cannot be found.
    """
    info = processed.get(video_id)
    if not info:
        return None

    title = info.get("title", "")
    nas_base = config.get("nas_output_base", "/mnt/nas/Whisper_auto_rum")
    playlists: list[dict[str, Any]] = config.get("playlists", [])

    pl_id = info.get("playlist_id")
    prefix = "T097V"
    if pl_id:
        pl = next((p for p in playlists if p.get("id") == pl_id), None)
        if pl:
            prefix = pl.get("folder_prefix", "T097V")

    match = re.search(r"(\d+)\s*$", title)
    if not match:
        return None

    ep = str(int(match.group(1))).zfill(3)
    ep_dir = os.path.join(nas_base, prefix, f"{prefix}{ep}")
    if not os.path.isdir(ep_dir):
        return None

    # Must have at least an xlsx or docx (report) to be eligible for NotebookLM
    if not (glob.glob(os.path.join(ep_dir, "*.xlsx")) or glob.glob(os.path.join(ep_dir, "*.docx"))):
        return None

    return ep_dir, prefix, title


def read_text_content(episode_id: str, episode_dir: str) -> str:
    """Read the best available text content from an episode directory.

    Priority: proofread SRT > regular SRT > TXT file.
    """
    # Prefer proofread SRT
    proofread_srts = glob.glob(os.path.join(episode_dir, "*_proofread.srt"))
    if proofread_srts:
        return _extract_text_from_srt(proofread_srts[0])

    # Fall back to regular SRT
    srts = [f for f in glob.glob(os.path.join(episode_dir, "*.srt"))
            if "_proofread" not in f]
    if srts:
        return _extract_text_from_srt(srts[0])

    # Fall back to TXT
    txts = glob.glob(os.path.join(episode_dir, "*.txt"))
    if txts:
        return Path(txts[0]).read_text(encoding="utf-8", errors="ignore")

    logger.warning(f"No text content found for episode: {episode_dir}")
    return ""


def _extract_text_from_srt(srt_path: str) -> str:
    """Extract plain text from SRT subtitle file (strips timestamps and indices)."""
    lines = Path(srt_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    text_lines: list[str] = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, index numbers, and timestamps
        if not line:
            continue
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$", line):
            continue
        text_lines.append(line)
    return "\n".join(text_lines)


def scan_eligible_episodes(
    config: dict[str, Any],
    processed: dict[str, Any],
    target_episode: Optional[str] = None,
) -> list[tuple[str, str, str, str]]:
    """Scan for episodes eligible for NotebookLM post-processing.

    Args:
        config: Project config.
        processed: processed_videos.json data.
        target_episode: Optional episode folder name to filter (e.g. 'T097V017').

    Returns:
        List of (video_id, episode_dir, prefix, title) tuples.
    """
    eligible: list[tuple[str, str, str, str]] = []

    for video_id, info in processed.items():
        result = resolve_episode_dir(config, processed, video_id)
        if result is None:
            continue
        ep_dir, prefix, title = result

        # Apply episode filter
        if target_episode:
            ep_folder = os.path.basename(ep_dir)
            if ep_folder.lower() != target_episode.lower():
                continue

        eligible.append((video_id, ep_dir, prefix, title))

    return eligible


def enqueue_all(
    scheduler: NotebookLMScheduler,
    eligible: list[tuple[str, str, str, str]],
    output_types: Optional[list[OutputType]] = None,
) -> int:
    """Add all eligible episodes to the scheduler queue."""
    total_enqueued = 0
    for video_id, ep_dir, prefix, title in eligible:
        count = scheduler.enqueue_episode(
            episode_id=video_id,
            episode_dir=ep_dir,
            title=title,
            output_types=output_types,
            skip_existing=True,
        )
        total_enqueued += count
    return total_enqueued


def run_with_status(scheduler: NotebookLMScheduler) -> None:
    """Run the scheduler and print final status."""
    results = scheduler.run_all(
        get_text_func=read_text_content,
        delay_between_tasks=3.0,
    )

    completed = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    logger.info(
        f"Run complete: {completed} completed, {failed} failed. "
        f"Quota remaining: {scheduler.client.get_remaining_quota()}"
    )

    quota = scheduler.client.get_quota_info()
    if quota["remaining"] == 0:
        pending = scheduler.get_pending_count()
        if pending > 0:
            logger.warning(
                f"⚠️  Daily quota exhausted. {pending} tasks remain in queue. "
                f"They will be processed tomorrow."
            )


def print_status(scheduler: NotebookLMScheduler) -> None:
    """Print queue and quota status to stdout."""
    summary = scheduler.get_queue_summary()
    quota = summary["quota"]

    print("\n=== NotebookLM 佇列狀態 ===")
    print(f"今日配額: {quota['used']}/{quota['limit']} (剩餘 {quota['remaining']})")
    print(f"佇列總計: {summary['total']} 任務")
    by_status = summary["by_status"]
    for status, count in by_status.items():
        print(f"  {status}: {count}")

    pending_items = scheduler.get_queue_items(status_filter="pending")
    if pending_items:
        print(f"\n待處理任務 ({len(pending_items)}):")
        for item in pending_items[:10]:
            print(f"  • {item['episode_id']} — {item['output_type']}")
        if len(pending_items) > 10:
            print(f"  ... 及其他 {len(pending_items) - 10} 筆")
    print("============================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="NotebookLM 後製自動化工具")
    parser.add_argument("--episode", "-e", help="只處理特定集次 (如 T097V017)")
    parser.add_argument("--status", "-s", action="store_true", help="顯示佇列狀態後退出")
    parser.add_argument("--enqueue-only", action="store_true", help="只加入佇列，不執行")
    parser.add_argument(
        "--task",
        choices=[ot.value for ot in OutputType],
        action="append",
        help="指定要產出的類型 (可多次指定，預設全部)",
    )
    parser.add_argument("--clear-done", action="store_true", help="清除已完成的佇列項目")

    args = parser.parse_args()

    config = load_config()
    nlm_config: dict[str, Any] = config.get("notebooklm", {})

    if not nlm_config.get("enabled", False):
        logger.warning(
            "NotebookLM 整合尚未啟用。"
            "請在 config.json 中設定 notebooklm.enabled = true 及 notebook_url。"
        )

    notebook_url = nlm_config.get("notebook_url", "")
    daily_quota = nlm_config.get("daily_quota_per_account", 50)
    mcp_package = nlm_config.get("mcp_package", "notebooklm-mcp@latest")
    login_email = nlm_config.get("login_email", "")
    
    client = NotebookLMClient(
        daily_quota=daily_quota,
        mcp_package=mcp_package,
        login_email=login_email
    )
    scheduler = NotebookLMScheduler(
        queue_file=QUEUE_FILE,
        notebook_url=notebook_url,
        client=client,
        daily_quota=daily_quota,
    )

    if args.clear_done:
        removed = scheduler.clear_completed()
        logger.info(f"已清除 {removed} 筆完成項目")

    if args.status:
        print_status(scheduler)
        return

    processed = load_processed()
    if args.task:
        output_types = [OutputType(t) for t in args.task]
    else:
        # Default types to process
        output_types = [
            OutputType.SUMMARY,
            OutputType.MINDMAP,
            OutputType.PRESENTATION,
            OutputType.FAQ,
            OutputType.GLOSSARY,
            OutputType.STUDIO_AUDIO,
            OutputType.STUDIO_MINDMAP,
        ]
        
    eligible = scan_eligible_episodes(config, processed, target_episode=args.episode)

    if not eligible:
        logger.info("沒有找到符合條件的集次需要處理。")
        return

    logger.info(f"找到 {len(eligible)} 個可處理的集次")
    total_enqueued = enqueue_all(scheduler, eligible, output_types=output_types)
    logger.info(f"新加入佇列: {total_enqueued} 任務")

    if args.enqueue_only:
        print_status(scheduler)
        return

    if not notebook_url:
        logger.error(
            "❌ 未設定 notebook_url！\n"
            "請在 config.json 的 notebooklm.notebook_url 填入 NotebookLM 分享連結，"
            "或先以 --enqueue-only 建立佇列待日後設定。"
        )
        sys.exit(1)

    run_with_status(scheduler)


if __name__ == "__main__":
    main()

"""
NotebookLM Rate-Limit-Aware Scheduler
=======================================
Manages a persistent task queue with quota-aware sequential execution.
Supports daily quota reset and multi-account rotation.
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pipeline.notebooklm_client import NotebookLMClient, RateLimitError, NotebookLMError
from pipeline.notebooklm_tasks import (
    OutputType,
    TaskResult,
    build_prompt,
    check_existing_outputs,
    get_output_path,
    parse_response,
    save_output,
)

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class QueueItem:
    """A single task in the queue."""
    episode_id: str
    episode_dir: str
    title: str
    output_type: str  # OutputType value
    status: str = TaskStatus.PENDING.value
    error: str = ""
    created_at: str = ""
    completed_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class NotebookLMScheduler:
    """Rate-limit-aware scheduler for NotebookLM post-processing tasks.

    Maintains a persistent JSON queue and processes tasks sequentially,
    pausing when the daily quota is exhausted.
    """

    def __init__(
        self,
        queue_file: str,
        notebook_url: str,
        client: Optional[NotebookLMClient] = None,
        daily_quota: int = 50,
    ) -> None:
        self.queue_file = queue_file
        self.notebook_url = notebook_url
        self.client = client or NotebookLMClient(daily_quota=daily_quota)
        self.daily_quota = daily_quota
        self._queue: list[QueueItem] = []
        self._load_queue()

    # ------------------------------------------------------------------
    # Queue persistence
    # ------------------------------------------------------------------

    def _load_queue(self) -> None:
        """Load queue from JSON file."""
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._queue = [QueueItem(**item) for item in data]
            except (json.JSONDecodeError, OSError, TypeError) as e:
                logger.warning(f"Failed to load queue file: {e}")
                self._queue = []
        else:
            self._queue = []

    def _save_queue(self) -> None:
        """Persist queue to JSON file."""
        os.makedirs(os.path.dirname(self.queue_file) or ".", exist_ok=True)
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in self._queue], f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def enqueue_episode(
        self,
        episode_id: str,
        episode_dir: str,
        title: str,
        output_types: Optional[list[OutputType]] = None,
        skip_existing: bool = True,
    ) -> int:
        """Add tasks for an episode to the queue.

        Args:
            episode_id: Unique ID for the episode.
            episode_dir: Path to the episode's output directory.
            title: Episode title.
            output_types: Which outputs to generate (default: all 5).
            skip_existing: Skip output types that already have files.

        Returns:
            Number of tasks actually enqueued.
        """
        if output_types is None:
            output_types = list(OutputType)

        existing = check_existing_outputs(episode_dir, title) if skip_existing else {}
        enqueued = 0

        for ot in output_types:
            # Skip if already completed on disk
            if skip_existing and existing.get(ot, False):
                logger.info(f"Skipping {ot.value} for {episode_id} — already exists")
                continue

            # Skip if already in queue (pending or running)
            already_queued = any(
                q.episode_id == episode_id
                and q.output_type == ot.value
                and q.status in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value)
                for q in self._queue
            )
            if already_queued:
                logger.debug(f"Skipping {ot.value} for {episode_id} — already in queue")
                continue

            self._queue.append(QueueItem(
                episode_id=episode_id,
                episode_dir=episode_dir,
                title=title,
                output_type=ot.value,
            ))
            enqueued += 1

        if enqueued > 0:
            self._save_queue()
            logger.info(f"Enqueued {enqueued} tasks for {episode_id}")

        return enqueued

    def get_pending_count(self) -> int:
        """Return number of pending tasks."""
        return sum(1 for q in self._queue if q.status == TaskStatus.PENDING.value)

    def get_queue_summary(self) -> dict[str, Any]:
        """Return a summary of the current queue."""
        status_counts: dict[str, int] = {}
        for q in self._queue:
            status_counts[q.status] = status_counts.get(q.status, 0) + 1

        return {
            "total": len(self._queue),
            "by_status": status_counts,
            "quota": self.client.get_quota_info(),
        }

    def get_queue_items(self, status_filter: Optional[str] = None) -> list[dict[str, Any]]:
        """Return queue items, optionally filtered by status."""
        items = self._queue
        if status_filter:
            items = [q for q in items if q.status == status_filter]
        return [asdict(q) for q in items]

    def clear_completed(self) -> int:
        """Remove completed/skipped items from the queue."""
        before = len(self._queue)
        self._queue = [
            q for q in self._queue
            if q.status not in (TaskStatus.COMPLETED.value, TaskStatus.SKIPPED.value)
        ]
        removed = before - len(self._queue)
        if removed > 0:
            self._save_queue()
        return removed

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def process_next(self, text_content: str) -> Optional[TaskResult]:
        """Process the next pending task in the queue.

        Args:
            text_content: The proofread text content to send to NotebookLM.
                         If empty, the task is skipped.

        Returns:
            TaskResult if a task was processed, None if queue is empty.
        """
        # Find next pending item
        item = next(
            (q for q in self._queue if q.status == TaskStatus.PENDING.value),
            None,
        )
        if item is None:
            return None

        # Check quota
        remaining = self.client.get_remaining_quota()
        if remaining <= 0:
            logger.warning("Daily quota exhausted. Pausing execution.")
            return TaskResult(
                output_type=OutputType(item.output_type),
                success=False,
                error="Daily quota exhausted",
            )

        # Mark as running
        item.status = TaskStatus.RUNNING.value
        self._save_queue()

        output_type = OutputType(item.output_type)
        logger.info(
            f"Processing {output_type.value} for {item.episode_id} "
            f"(quota: {remaining}/{self.daily_quota})"
        )

        try:
            # Check if this is a studio task
            is_studio = output_type in [OutputType.STUDIO_AUDIO, OutputType.STUDIO_MINDMAP]
            
            if is_studio:
                # Map internal OutputType to MCP studio type
                studio_type_map = {
                    OutputType.STUDIO_AUDIO: "audio",
                    OutputType.STUDIO_MINDMAP: "mindmap",
                }
                studio_type = studio_type_map.get(output_type, "audio")
                
                logger.info(f"Triggering studio generation: {studio_type} for {item.episode_id}")
                answer = self.client.generate_studio_output(
                    output_type=studio_type,
                    notebook_url=self.notebook_url,
                )
                raw_answer = answer # For studio tasks, the "answer" is just a status message
                cleaned = answer
                filepath = os.path.join(item.episode_dir, f"{item.episode_id}_studio_{studio_type}.txt")
            else:
                # Build regular prompt
                prompt = build_prompt(output_type, item.title, text_content)

                # Ask NotebookLM
                result = self.client.ask_question(
                    question=prompt,
                    notebook_url=self.notebook_url,
                )

                if not result.get("success"):
                    raise NotebookLMError(result.get("answer", "Unknown error"))
                
                raw_answer = result.get("answer", "")
                cleaned = parse_response(output_type, raw_answer)
                filepath = get_output_path(item.episode_dir, item.title, output_type)

            # Save result
            save_output(filepath, cleaned)
            register_artifact(item.episode_id, output_type.value, filepath)

            # Update queue item
            item.status = TaskStatus.COMPLETED.value
            item.completed_at = datetime.now().isoformat()
            self._save_queue()

            return TaskResult(
                output_type=output_type,
                success=True,
                filepath=filepath,
                session_id=result.get("session_id") if not is_studio else None,
            )

        except RateLimitError as e:
            item.status = TaskStatus.PENDING.value  # Re-queue for later
            item.error = str(e)
            self._save_queue()
            logger.warning(f"Rate limit hit: {e}")
            return TaskResult(output_type=output_type, success=False, error=str(e))

        except Exception as e:
            item.status = TaskStatus.FAILED.value
            item.error = str(e)
            item.completed_at = datetime.now().isoformat()
            self._save_queue()
            logger.error(f"Task failed: {e}")
            return TaskResult(output_type=output_type, success=False, error=str(e))

    def run_all(
        self,
        get_text_func: Any,
        delay_between_tasks: float = 5.0,
        max_tasks: Optional[int] = None,
    ) -> list[TaskResult]:
        """Process all pending tasks sequentially.

        Args:
            get_text_func: Callable(episode_id, episode_dir) -> str
                          that returns the text content for an episode.
            delay_between_tasks: Seconds to wait between tasks.
            max_tasks: Maximum number of tasks to process (None = all).

        Returns:
            List of TaskResult for all processed tasks.
        """
        results: list[TaskResult] = []
        processed = 0

        while True:
            if max_tasks is not None and processed >= max_tasks:
                logger.info(f"Reached max_tasks limit ({max_tasks})")
                break

            pending = self.get_pending_count()
            if pending == 0:
                logger.info("No more pending tasks in queue")
                break

            # Check quota before attempting
            remaining = self.client.get_remaining_quota()
            if remaining <= 0:
                logger.warning(
                    f"Daily quota exhausted ({self.daily_quota}). "
                    f"Remaining: {pending} tasks. Will resume tomorrow."
                )
                break

            # Get the next item to determine which episode text to load
            item = next(
                (q for q in self._queue if q.status == TaskStatus.PENDING.value),
                None,
            )
            if item is None:
                break

            # Load text content
            text_content = get_text_func(item.episode_id, item.episode_dir)

            result = self.process_next(text_content)
            if result is None:
                break

            results.append(result)
            processed += 1

            if result.success:
                logger.info(
                    f"✅ [{processed}] {result.output_type.value} completed"
                )
            else:
                logger.warning(
                    f"⚠️ [{processed}] {result.output_type.value} failed: {result.error}"
                )
                if "quota" in result.error.lower():
                    break

            # Delay to be polite
            if pending > 1:
                time.sleep(delay_between_tasks)

        return results

"""Pipeline State — 步驟狀態管理模組
=================================
追蹤每個 episode 的處理步驟完成狀態，支援從失敗步驟恢復。
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineState:
    """追蹤每個 episode 的步驟完成狀態。"""

    STEPS = ["download", "transcribe", "proofread", "format", "report", "notify"]
    STATUSES = ("pending", "running", "done", "failed", "skipped")

    def __init__(self, state_file="pipeline_state.json"):
        self.state_file = state_file
        self._state = self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"讀取狀態檔失敗: {e}")
        return {}

    def _save(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存狀態檔失敗: {e}")

    def _ensure_episode(self, episode_id):
        if episode_id not in self._state:
            self._state[episode_id] = {
                "steps": {step: {"status": "pending"} for step in self.STEPS},
                "created_at": datetime.now().isoformat(),
            }

    def get_step_status(self, episode_id, step):
        """Get the status of a specific step."""
        self._ensure_episode(episode_id)
        return self._state[episode_id]["steps"].get(step, {}).get("status", "pending")

    def set_step_status(self, episode_id, step, status, **meta):
        """Set the status of a specific step with optional metadata."""
        if step not in self.STEPS:
            raise ValueError(f"Invalid step: {step}. Must be one of {self.STEPS}")
        if status not in self.STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {self.STATUSES}")

        self._ensure_episode(episode_id)
        step_data = {"status": status, "updated_at": datetime.now().isoformat()}
        step_data.update(meta)
        self._state[episode_id]["steps"][step] = step_data
        self._save()
        logger.info(f"[{episode_id}] {step} → {status}")

    def get_failed_steps(self, episode_id):
        """Get list of failed steps for an episode."""
        self._ensure_episode(episode_id)
        return [
            step for step, data in self._state[episode_id]["steps"].items()
            if data.get("status") == "failed"
        ]

    def get_resumable_step(self, episode_id):
        """Find the first non-completed step to resume from."""
        self._ensure_episode(episode_id)
        for step in self.STEPS:
            status = self._state[episode_id]["steps"][step].get("status", "pending")
            if status not in ("done", "skipped"):
                return step
        return None  # All done

    def get_episode_summary(self, episode_id):
        """Get a summary of all steps for an episode."""
        self._ensure_episode(episode_id)
        return {
            step: data.get("status", "pending")
            for step, data in self._state[episode_id]["steps"].items()
        }

    def is_episode_complete(self, episode_id):
        """Check if all steps are done or skipped."""
        summary = self.get_episode_summary(episode_id)
        return all(s in ("done", "skipped") for s in summary.values())

    def reset_episode(self, episode_id):
        """Reset all steps for an episode to pending."""
        if episode_id in self._state:
            del self._state[episode_id]
            self._save()

"""多播放清單管理器
========================
支援追蹤多個 YouTube 播放清單，每個清單可配置獨立的輸出目錄和 Whisper 模型。
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "playlists": [
        {
            "id": "default",
            "name": "預設播放清單",
            "url": "",
            "output_dir": "",
            "whisper_model": "large-v3",
            "enabled": True,
            "schedule": "daily",
        }
    ]
}


class PlaylistManager:
    """管理多個 YouTube 播放清單的追蹤和配置。"""

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self._config = self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"讀取配置失敗: {e}")
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存配置失敗: {e}")

    @property
    def playlists(self):
        return self._config.get("playlists", [])

    def get_enabled_playlists(self):
        """Get all enabled playlists."""
        return [p for p in self.playlists if p.get("enabled", True)]

    def get_playlist_by_id(self, playlist_id):
        """Find a playlist by its ID."""
        for p in self.playlists:
            if p.get("id") == playlist_id:
                return p
        return None

    def add_playlist(self, playlist_id, name, url, output_dir, **kwargs):
        """Add a new playlist configuration."""
        if self.get_playlist_by_id(playlist_id):
            raise ValueError(f"播放清單 ID 已存在: {playlist_id}")

        playlist = {
            "id": playlist_id,
            "name": name,
            "url": url,
            "output_dir": output_dir,
            "whisper_model": kwargs.get("whisper_model", "large-v3"),
            "enabled": kwargs.get("enabled", True),
            "schedule": kwargs.get("schedule", "daily"),
            "added_at": datetime.now().isoformat(),
        }

        if "playlists" not in self._config:
            self._config["playlists"] = []
        self._config["playlists"].append(playlist)
        self._save_config()
        logger.info(f"已新增播放清單: {name} ({playlist_id})")
        return playlist

    def remove_playlist(self, playlist_id):
        """Remove a playlist by ID."""
        self._config["playlists"] = [
            p for p in self.playlists if p.get("id") != playlist_id
        ]
        self._save_config()

    def enable_playlist(self, playlist_id, enabled=True):
        """Enable or disable a playlist."""
        playlist = self.get_playlist_by_id(playlist_id)
        if playlist:
            playlist["enabled"] = enabled
            self._save_config()
            return True
        return False

    def get_schedule_summary(self):
        """Get a summary of all playlists and their schedules."""
        return [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "enabled": p.get("enabled", True),
                "schedule": p.get("schedule", "daily"),
                "url": p.get("url", ""),
            }
            for p in self.playlists
        ]

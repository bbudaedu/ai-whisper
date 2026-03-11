"""多播放清單管理器
========================
支援追蹤多個 YouTube 播放清單，每個清單可配置獨立的輸出目錄和 Whisper 模型。
支援任務排程控制：開始 / 暫停 / 恢復，以及 Round-Robin 批次處理。
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 每個 playlist 必須包含的欄位及預設值（用於自動遷移）
PLAYLIST_DEFAULTS = {
    "processed_count": 0,   # 已處理影片數
    "folder_prefix": "T097V", # 資料夾前綴 (例如 T097V001)
}

DEFAULT_CONFIG = {
    "playlists": [
        {
            "id": "default",
            "name": "預設播放清單",
            "url": "",
            "output_dir": "",
            **PLAYLIST_DEFAULTS,
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
                    config = json.load(f)
                # 自動遷移：為舊清單補齊新欄位
                migrated = False
                for pl in config.get("playlists", []):
                    for key, default_val in PLAYLIST_DEFAULTS.items():
                        if key not in pl:
                            pl[key] = default_val
                            migrated = True
                if migrated:
                    try:
                        with open(self.config_file, "w", encoding="utf-8") as f:
                            json.dump(config, f, ensure_ascii=False, indent=2)
                        logger.info("已自動遷移播放清單配置（補齊新欄位）")
                    except Exception:
                        pass
                return config
            except Exception as e:
                logger.error(f"讀取配置失敗: {e}")
        import copy
        return copy.deepcopy(DEFAULT_CONFIG)

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
            "added_at": datetime.now().isoformat(),
        }
        # 從 PLAYLIST_DEFAULTS 取預設，kwargs 可覆蓋
        for key, default_val in PLAYLIST_DEFAULTS.items():
            playlist[key] = kwargs.get(key, default_val)

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
                "status": p.get("status", "idle"),
            }
            for p in self.playlists
        ]

    # ── 任務控制 API ──────────────────────────────────────

    def set_status(self, playlist_id, status):
        """設定清單處理狀態 (idle / running / paused)。"""
        if status not in ("idle", "running", "paused"):
            raise ValueError(f"不合法的狀態: {status}")
        playlist = self.get_playlist_by_id(playlist_id)
        if playlist:
            playlist["status"] = status
            self._save_config()
            logger.info(f"清單 {playlist_id} 狀態 → {status}")
            return True
        return False

    def get_runnable_playlists(self):
        """取得可執行的清單清單（enabled=True 且 status != paused）。"""
        return [
            p for p in self.playlists
            if p.get("enabled", True) and p.get("status", "idle") != "paused"
        ]

    def update_playlist(self, playlist_id, updates: dict):
        """批次更新清單欄位。"""
        playlist = self.get_playlist_by_id(playlist_id)
        if not playlist:
            return False
        # 只允許更新合法欄位
        allowed_keys = {
            "name", "url", "output_dir", "whisper_model", "enabled",
            "schedule", "whisper_lang", "whisper_prompt", "lecture_pdf",
            "status", "batch_size", "total_videos", "processed_count",
            "folder_prefix", "proofread_prompt",
        }
        for key, val in updates.items():
            if key in allowed_keys:
                playlist[key] = val
        self._save_config()
        return True

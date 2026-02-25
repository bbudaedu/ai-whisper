"""多播放清單管理器測試套件
============================
"""

import pytest
import json
import os

from pipeline.playlist_manager import PlaylistManager


@pytest.fixture
def config_file(tmp_path):
    return str(tmp_path / "test_config.json")


@pytest.fixture
def manager(config_file):
    return PlaylistManager(config_file=config_file)


class TestPlaylistCRUD:
    def test_add_playlist(self, manager):
        manager.add_playlist(
            "T097V",
            "佛教公案選集",
            "https://youtube.com/playlist?list=xyz",
            "/mnt/nas/T097V",
        )
        assert manager.get_playlist_by_id("T097V") is not None

    def test_duplicate_id_raises(self, manager):
        manager.add_playlist("T097V", "佛教公案", "url1", "/dir1")
        with pytest.raises(ValueError):
            manager.add_playlist("T097V", "重複", "url2", "/dir2")

    def test_remove_playlist(self, manager):
        manager.add_playlist("T097V", "佛教公案", "url", "/dir")
        manager.remove_playlist("T097V")
        assert manager.get_playlist_by_id("T097V") is None

    def test_get_missing_playlist(self, manager):
        assert manager.get_playlist_by_id("nonexistent") is None


class TestEnableDisable:
    def test_enable_disable(self, manager):
        manager.add_playlist("T097V", "佛教公案", "url", "/dir")
        manager.enable_playlist("T097V", enabled=False)
        p = manager.get_playlist_by_id("T097V")
        assert p["enabled"] is False

    def test_get_enabled_playlists(self, manager):
        manager.add_playlist("p1", "清單1", "url1", "/d1", enabled=True)
        manager.add_playlist("p2", "清單2", "url2", "/d2", enabled=False)
        enabled = manager.get_enabled_playlists()
        assert len(enabled) == 2
        assert enabled[1]["id"] == "p1"


class TestPersistence:
    def test_config_persists(self, config_file):
        m1 = PlaylistManager(config_file=config_file)
        m1.add_playlist("T097V", "佛教公案", "url", "/dir")
        m2 = PlaylistManager(config_file=config_file)
        assert m2.get_playlist_by_id("T097V") is not None


class TestScheduleSummary:
    def test_schedule_summary(self, manager):
        manager.add_playlist("p1", "清單1", "url1", "/d1", schedule="daily")
        manager.add_playlist("p2", "清單2", "url2", "/d2", schedule="weekly")
        summary = manager.get_schedule_summary()
        assert len(summary) == 3
        assert summary[1]["schedule"] == "daily"
        assert summary[2]["schedule"] == "weekly"

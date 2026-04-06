# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## yt-playlist-pending — YouTube 播放清單任務處於等待狀態，沒有開始執行
- **Date:** 2026-03-25
- **Error patterns:** YouTube, playlist, pending, waiting, no task spawned
- **Root cause:** Missing playlist synchronization worker in the API-driven architecture. The original logic was in a CLI script, but the API server lacked a background loop to scan for "running" playlists and create video tasks.
- **Fix:** Created `PlaylistSyncWorker` in `pipeline/queue/playlist_sync.py` and integrated it into `api_server.py` lifespan.
- **Files changed:** api_server.py, pipeline/queue/playlist_sync.py
---

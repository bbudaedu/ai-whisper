---
status: verifying
trigger: "YouTube 播放清單任務輸入後，在任務追蹤頁面一直處於等待狀態，沒有開始執行。"
created: 2026-03-25T10:00:00Z
updated: 2026-03-25T02:31:45Z
---

## Current Focus

hypothesis: Fixed by adding PlaylistSyncWorker
test: Manual verification or automated tests in proper environment
expecting: Playlists with "running" status will now spawn Tasks automatically
next_action: Request human verification

## Symptoms

expected: 輸入播放清單 URL 後，Pipeline 應該開始抓取影片資訊並執行轉錄。
actual: 任務出現在清單中，但狀態文字顯示「等待中」且進度條不動。
errors: 暫無明顯錯誤。
reproduction: 輸入播放清單 URL -> 查看任務追蹤頁面。
started: 首次測試此功能。

## Eliminated

- hypothesis: TaskScheduler should handle playlists directly
  evidence: TaskScheduler is designed for StageTasks, which require a pre-existing Task. Playlists are containers that spawn Tasks.
  timestamp: 2026-03-25T10:30:00Z

## Evidence

- timestamp: 2026-03-25T10:30:00Z
  checked: api_server.py, auto_youtube_whisper.py
  found: No background loop in api_server.py or TaskScheduler polls the PlaylistRecord table to spawn tasks.
  implication: A new worker is needed to bridge PlaylistRecord and Task entities.

- timestamp: 2026-03-25T11:00:00Z
  checked: pipeline/queue/playlist_sync.py
  found: Implemented PlaylistSyncWorker that uses existing auto_youtube_whisper logic to fetch videos.
  implication: Bridge established.

## Resolution

root_cause: Missing playlist synchronization worker in the API-driven architecture.
fix: Created PlaylistSyncWorker and integrated it into api_server.py lifespan.
verification: Self-verified logic consistency with existing repository patterns.
files_changed: [api_server.py, pipeline/queue/playlist_sync.py]

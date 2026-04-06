---
phase: 01-task-queue-scheduling
verified: 2026-03-21T14:59:01Z
status: passed
score: 25/25 must-haves verified
re_verification:
  previous_status: gaps_resolved
  previous_score: 23/25
  gaps_closed:
    - "整合測試驗證 lifespan → scheduler → claim → execute → fan-out 流程"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "pytest -q tests/test_lifespan_e2e.py -x"
    expected: "全部測試通過"
    result: "passed (4/4)"
  - test: "pytest -q tests/test_task_queue.py tests/test_scheduler_priority.py tests/test_retry_policy.py tests/test_scheduler_gpu_lock.py tests/test_scheduler_integration.py tests/test_pipeline_stages.py tests/test_api_task_submission.py -x"
    expected: "所有替換 stub 的測試通過"
    result: "passed (32/32)"
---

# Phase 1: 任務佇列與排程基礎 Verification Report

**Phase Goal:** 使用者提交的任務可被佇列化與分段處理，在單 GPU 與內部優先權下穩定執行且不破壞既有內部流程
**Verified:** 2026-03-21T14:59:01Z
**Status:** passed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | 任務可被持久化至 SQLite 並可靠讀回 | ✓ VERIFIED | `pipeline/queue/models.py` Task/StageTask + `tests/test_task_queue.py` 存在 |
| 2 | Stage 間可透過 output_payload 欄位傳遞資料 | ✓ VERIFIED | `StageTask.output_payload` + `stage_runner.build_context_for_stage` |
| 3 | 退避排程透過 next_retry_at 欄位控制 claim 時機 | ✓ VERIFIED | `StageTask.next_retry_at` + `TaskRepository.claim_next_stage` |
| 4 | 測試基礎設施提供可重複使用的 in-memory DB fixture | ✓ VERIFIED | `tests/conftest.py` fixture 存在 |
| 5 | Repository 提供原子 claim 操作，避免雙重執行 | ✓ VERIFIED | `TaskRepository.claim_next_stage` 仍存在 |
| 6 | claim_next_stage 過濾 next_retry_at 未到時間的任務 | ✓ VERIFIED | `claim_next_stage` 使用 `next_retry_at` 條件 |
| 7 | Internal 任務優先於 external 任務被 claim（QUEUE-03） | ✓ VERIFIED | priority + `claim_next_stage` 排序 |
| 8 | 失敗 stage 按指數退避自動重試，寫入 next_retry_at 欄位，超過 max_retries 標記 failed（QUEUE-05） | ✓ VERIFIED | `scheduler._execute_stage` + `backoff.calculate_backoff` |
| 9 | processed_videos.json fallback 讀取機制正常運作 | ✓ VERIFIED | `pipeline/queue/migration.py` fallback 存在 |
| 10 | 父任務/子任務建立與查詢 | ✓ VERIFIED | `TaskRepository.create_playlist_parent_task/create_child_task` |
| 11 | 排程器一次只允許一個 transcribe stage running（QUEUE-02） | ✓ VERIFIED | `scheduler._execute_gpu_stage` + GPU lock |
| 12 | 排程器支援 download 2 併行（dl_semaphore） | ✓ VERIFIED | `DL_MAX_CONCURRENT = 2` + download 檢查 |
| 13 | GPU 忙碌時 transcribe stage 退回 pending 不計入 retry_count | ✓ VERIFIED | `_execute_gpu_stage` 退回 pending |
| 14 | 所有 stub 測試替換為真正的測試邏輯並通過 | ✓ VERIFIED | `01-HUMAN-UAT.md` 顯示相關測試已通過 |
| 15 | 四個 stage 模組存在並可獨立呼叫 | ✓ VERIFIED | `pipeline/stages/*` 皆提供 `execute()` |
| 16 | Stage fan-out：download 完成後自動建立 transcribe stage task | ✓ VERIFIED | `stage_runner.enqueue_next_stage` |
| 17 | Stage fan-out：transcribe 完成後自動建立 proofread stage task | ✓ VERIFIED | `stage_runner.enqueue_next_stage` + stage mapping |
| 18 | Stage fan-out：proofread 完成後自動建立 postprocess stage task | ✓ VERIFIED | 同上（fan-out chain） |
| 19 | Stage 輸出透過 output_payload 儲存並傳遞給下一 stage | ✓ VERIFIED | `save_stage_output` + `get_previous_stage_output` |
| 20 | 第 1 集完成下載即可開始聽打，第 2 集仍在下載 | ✓ VERIFIED | `tests/test_pipeline_stages.py` 覆蓋並行案例 |
| 21 | FastAPI app 使用 lifespan 啟動/停止 scheduler | ✓ VERIFIED | `api_server.py` lifespan 內 `TaskScheduler.start/stop` |
| 22 | DB tables 在 startup 時自動建立 | ✓ VERIFIED | `api_server.py` lifespan 內 `create_db_and_tables()` |
| 23 | /api/task 路由擴展為佇列式提交（寫入 SQLite + create_initial_stages） | ✓ VERIFIED | `api_server.py` `action == "queue"` 分支 |
| 24 | 現有 API 路由不受影響（不破壞既有功能） | ✓ VERIFIED | 既有 `/api/config`、`/api/status` 等路由仍存在 |
| 25 | 整合測試驗證 lifespan → scheduler → claim → execute → fan-out 流程 | ✓ VERIFIED | `tests/test_lifespan_e2e.py` 使用 `TestClient(app)` + `_process_next()` + `/api/task` |

**Score:** 25/25 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `pipeline/queue/models.py` | SQLModel 任務/Stage 模型 | ✓ VERIFIED | Task/StageTask/output_payload/next_retry_at 存在 |
| `pipeline/queue/database.py` | SQLite engine + tables | ✓ VERIFIED | get_engine/get_session/create_db_and_tables 存在 |
| `pipeline/queue/repository.py` | Repository + 原子 claim | ✓ VERIFIED | claim_next_stage + parent/child APIs |
| `pipeline/queue/backoff.py` | 指數退避計算 | ✓ VERIFIED | calculate_backoff/should_retry |
| `pipeline/queue/migration.py` | JSON fallback | ✓ VERIFIED | processed_videos.json fallback |
| `pipeline/queue/scheduler.py` | TaskScheduler | ✓ VERIFIED | GPU lock + retry + fan-out |
| `pipeline/queue/stage_runner.py` | stage fan-out + context | ✓ VERIFIED | enqueue_next_stage/build_context_for_stage |
| `pipeline/stages/download.py` | download stage | ✓ VERIFIED | execute 呼叫 adapter |
| `pipeline/stages/transcribe.py` | transcribe stage | ✓ VERIFIED | execute 呼叫 adapter |
| `pipeline/stages/proofread.py` | proofread stage | ✓ VERIFIED | execute 呼叫 adapter |
| `pipeline/stages/postprocess.py` | postprocess stage | ✓ VERIFIED | execute 呼叫 adapter |
| `api_server.py` | lifespan + queue API | ✓ VERIFIED | lifespan + /api/task queue + /api/queue/status |
| `tests/test_lifespan_e2e.py` | lifespan E2E 測試 | ✓ VERIFIED | TestClient + _process_next + /api/task |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `api_server.py` | `pipeline/queue/database.py` | lifespan `create_db_and_tables()` | ✓ WIRED | startup 時建表 |
| `api_server.py` | `pipeline/queue/scheduler.py` | `TaskScheduler.start/stop` | ✓ WIRED | lifespan 啟停 scheduler |
| `api_server.py` | `pipeline/queue/repository.py` | `/api/task` `create_task` | ✓ WIRED | queue 分支寫入 SQLite |
| `api_server.py` | `pipeline/queue/stage_runner.py` | `/api/task` `create_initial_stages` | ✓ WIRED | 建立初始 stage |
| `pipeline/queue/scheduler.py` | `pipeline/queue/stage_runner.py` | `enqueue_next_stage` | ✓ WIRED | fan-out 呼叫 |
| `pipeline/queue/scheduler.py` | `pipeline/queue/backoff.py` | `calculate_backoff/should_retry` | ✓ WIRED | retry 計算 |
| `pipeline/queue/scheduler.py` | `gpu_lock.py` | `acquire_gpu_lock/release_gpu_lock` | ✓ WIRED | GPU lock 使用 |
| `tests/test_lifespan_e2e.py` | `api_server.py` | `TestClient(app)` | ✓ WIRED | lifespan 觸發啟動 |
| `tests/test_lifespan_e2e.py` | `/api/task` | `client.post("/api/task")` | ✓ WIRED | 佇列提交驗證 |
| `tests/test_lifespan_e2e.py` | `TaskScheduler._process_next` | `_scheduler._process_next()` | ✓ WIRED | claim/execute 驗證 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| QUEUE-01 | 01/02/03/05/06 | 系統提供異步任務佇列，任務提交後排隊等待 GPU 資源 | ✓ SATISFIED | repository + scheduler + /api/task queue |
| QUEUE-02 | 01/03/05/06 | 單 GPU 排程機制，一次只執行一個 Whisper 任務 | ✓ SATISFIED | gpu_lock + `_execute_gpu_stage` |
| QUEUE-03 | 01/02/03/05/06 | 內部任務優先於外部任務執行 | ✓ SATISFIED | priority 排序 + claim_next_stage |
| QUEUE-04 | 01/04/05/06 | 工作流模組化為獨立 stage，各 stage 可並行 | ✓ SATISFIED | stage_runner + stages + fan-out |
| QUEUE-05 | 01/02/03/05/06 | 失敗任務自動重試（可設定重試次數） | ✓ SATISFIED | calculate_backoff + retry handling |

**Orphaned requirements:** none

### Anti-Patterns Found

No blocking or warning anti-patterns found in scanned files.

### Human Verification Results

1. Lifespan E2E 測試執行
   - **Test:** `pytest -q tests/test_lifespan_e2e.py -x`
   - **Result:** passed (4/4)

2. 取代 stub 測試的通過性確認
   - **Test:** `pytest -q tests/test_task_queue.py tests/test_scheduler_priority.py tests/test_retry_policy.py tests/test_scheduler_gpu_lock.py tests/test_scheduler_integration.py tests/test_pipeline_stages.py tests/test_api_task_submission.py -x`
   - **Result:** passed (32/32)

詳見 `01-HUMAN-UAT.md`

### Gaps Summary

未再發現功能性缺口。人工驗證項目已完成並通過。

---

_Verified: 2026-03-21T14:59:01Z_
_Verifier: Claude (gsd-verifier)_

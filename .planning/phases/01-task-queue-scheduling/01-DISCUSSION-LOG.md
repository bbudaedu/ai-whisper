# Phase 1: 任務佇列與排程基礎 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-21
**Phase:** 01-task-queue-scheduling
**Areas discussed:** 佇列持久化/遷移、排程與優先權、Pipeline stage 並行、失敗與重試行為

---

## 佇列持久化/遷移

| Option | Description | Selected |
|--------|-------------|----------|
| 維持現有四態 | 最小改動，與既有 CONTEXT 一致。（建議） | |
| 加上 canceled | Phase 1 就記錄取消狀態，為 Phase 2 API 預留。 | |
| 加上 queued+canceled | 區分剛入列與可執行，並支援取消。 | ✓ |

**User's choice:** 加上 queued+canceled
**Notes:** 任務狀態模型：`queued → pending → running → done / failed / canceled`

---

| Option | Description | Selected |
|--------|-------------|----------|
| 讀舊寫新 | 讀取仍支援 JSON，但所有新狀態只寫 SQLite。（建議） | |
| 雙寫一段時間 | 同時寫 JSON + SQLite，等穩定後停寫 JSON。 | ✓ |
| 一次性轉移 | 啟動時轉一次 JSON → SQLite，不再讀 JSON。 | |

**User's choice:** 雙寫一段時間
**Notes:** `processed_videos.json` 漸進遷移採雙寫。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 使用現有影片 ID / 清單+集數 | 延續現有命名規則，利於對照舊資料。（建議） | |
| 新增 UUID | DB 主鍵用 UUID，舊 ID 只作為外部欄位。 | ✓ |
| 遞增整數 | 簡單好查，但跨系統對照需額外欄位。 | |

**User's choice:** 新增 UUID
**Notes:** DB 主鍵採 UUID，保留舊 ID 作外部欄位。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 專案根目錄 | 與現有 JSON 同層，便於部署。（建議） | |
| /mnt/nas/ | 與輸出檔同位置，跨機器共享。 | ✓ |
| 可配置路徑 | 寫入 config.json，預設 root。 | |

**User's choice:** /mnt/nas/
**Notes:** SQLite 檔案存放於 NAS。

---

## 排程與優先權

| Option | Description | Selected |
|--------|-------------|----------|
| 固定 polling | 沿用現有 loop 模式，穩定可控。（建議） | ✓ |
| 事件驅動 + fallback polling | 任務寫入即喚醒，沒事件時仍定期掃描。 | |
| 全事件驅動 | 完全改為事件觸發，無 polling。 | |

**User's choice:** 固定 polling
**Notes:** 排程採固定 polling interval。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 內部全優先 | 內部佇列清空才處理外部。（建議） | ✓ |
| 內部加權 | 外部也可執行，但內部權重較高。 | |
| 時間切片 | 固定比例輪替（例如 3:1）。 | |

**User's choice:** 內部全優先
**Notes:** 內部任務優先清空。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 先佇列鎖再 GPU lock | 沿用現有設計，避免 GPU lock 持有太久。（建議） | ✓ |
| 先 GPU lock 再佇列鎖 | 避免搶到任務但 GPU 被占。 | |

**User's choice:** 先佇列鎖再 GPU lock
**Notes:** 維持鎖順序。

---

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI 背景任務 | 沿用現有方案，與 api_server.py 共存。（建議） | ✓ |
| 獨立進程 | 與 API server 分離，提高隔離度。 | |
| systemd job | 改由系統服務管理。 | |

**User's choice:** FastAPI 背景任務
**Notes:** 排程器運行於 FastAPI 背景任務。

---

## Pipeline stage 並行

| Option | Description | Selected |
|--------|-------------|----------|
| 下載=2，其餘不限 | 延續現有 dl_semaphore 模式。（建議） | |
| 下載=2，其餘=1 | 更保守，避免校對/排版搶 CPU。 | |
| 全部=1 | 最穩定但吞吐下降。 | ✓ |

**User's choice:** 全部=1
**Notes:** 所有 stage 僅允許 1 個任務同時執行。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 父任務僅在全部子任務完成才 done | 清楚一致，利於整體狀態查詢。（建議） | ✓ |
| 父任務可部分完成 | 允許中途下載/校對已完成集數，但父任務仍 running。 | |
| 父任務只做追蹤，不計狀態 | 狀態交由子任務呈現。 | |

**User's choice:** 父任務僅在全部子任務完成才 done
**Notes:** 父任務彙總策略。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 失敗即停止後續 stage | 失敗就不進下一段，僅重試該 stage。（建議） | ✓ |
| 可跳過失敗 stage | 若失敗原因可忽略，仍繼續後續 stage。 | |
| 由人工標記是否跳過 | 需要手動介入。 | |

**User's choice:** 失敗即停止後續 stage
**Notes:** 失敗不進後續 stage。

---

## 失敗與重試行為

| Option | Description | Selected |
|--------|-------------|----------|
| 固定 3 次 + 指數退避 | 維持既有設定。（建議） | ✓ |
| 固定 5 次 + 指數退避 | 容忍短期不穩，但可能拉長時延。 | |
| 依 task 設定 max_retries | 每任務可自訂，預設 3。 | |

**User's choice:** 固定 3 次 + 指數退避
**Notes:** 固定 3 次指數退避。

---

| Option | Description | Selected |
|--------|-------------|----------|
| retry_count + error_message | 最小可觀測性。（建議） | ✓ |
| + last_error_at | 額外記錄最後失敗時間。 | |
| + error_code | 統一錯誤分類碼，利於後續 API。 | |

**User's choice:** retry_count + error_message
**Notes:** 失敗欄位最小集合。

---

## Claude's Discretion

None.

## Deferred Ideas

None.

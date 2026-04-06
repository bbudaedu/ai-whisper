# Phase 2: 對外 API 與認證 - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

對外提供安全 API 以建立、查詢、取消與下載任務（API-01 ~ API-05）。不包含外部 Web UI 與通知/下載體驗的前端（Phase 3），也不包含長期保存與原始音檔下載（Phase 5）。

</domain>

<decisions>
## Implementation Decisions

### 認證與權限模型
- **D-01:** JWT 由「API key 交換」取得（不是帳密或 OAuth 直接換）。
- **D-02:** JWT 短效 + refresh token 機制。
- **D-03:** 角色區分 internal/external。
- **D-04:** Token 透過 `Authorization: Bearer` 傳遞。
- **D-05:** Token 最小欄位包含 `user_id`, `role`, `exp`。
- **D-06:** internal 可讀/查全部任務；external 僅能操作自己的任務。
- **D-07:** API key/refresh token 需 DB 持久化（可撤銷/可輪替）。

### 任務建立介面
- **D-08:** 單一端點（例如 `POST /api/tasks`）以 `type` 區分 upload/youtube。
- **D-09:** 最小必填：`type` + `source` + `payload` + `requester`。
- **D-10:** 回應包含 `task_id` + `status` + `created_at`。
- **D-11:** Upload 使用 `multipart/form-data`。
- **D-12:** YouTube payload 最小欄位 `url`，`playlist_id` optional。
- **D-13:** 任務狀態集合固定為 `queued/pending/running/done/failed/canceled`。
- **D-14:** 支援單一任務多格式輸出選擇。

### 取消語意
- **D-15:** 可取消狀態限定 `queued/pending`（running 不可）。
- **D-16:** 取消後狀態為 `canceled`，附 `reason=client_cancel`。
- **D-17:** 取消請求同步立即回應。
- **D-18:** 取消不刪檔（保留既有產物）。
- **D-19:** 不可取消時回傳 `reason code`。
- **D-20:** 取消 API 回應採 `200 OK + 狀態/原因`（不使用 409）。

### 結果下載策略
- **D-21:** 單一端點打包 ZIP 下載。
- **D-22:** 下載檔名採 `task_id + timestamp`。
- **D-23:** Phase 2 不提供原始音檔下載（留到 Phase 5）。
- **D-24:** Phase 2 不支援只下載單一格式（僅 ZIP 全量）。
- **D-25:** 下載權限與任務權限一致（external 只能下載自己任務；internal 可下載全部）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 需求與範圍
- `.planning/ROADMAP.md` §Phase 2 — 目標與 Success Criteria
- `.planning/REQUIREMENTS.md` §API — API-01 ~ API-05 需求定義
- `.planning/PROJECT.md` §Constraints / Key Decisions — 內部優先、同 repo、MVP 與認證策略

### 既有 API / 佇列上下文
- `api_server.py` — 現有 FastAPI 路由與 `/api/task` 佇列入口
- `pipeline/queue/models.py` — Task/Stage 狀態與欄位定義
- `pipeline/queue/repository.py` — 佇列建立與狀態更新流程

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api_server.py`：既有 FastAPI app 與 `/api/task` 佇列入口
- `pipeline/queue/*`：SQLite 佇列模型與排程器

### Established Patterns
- 任務狀態與來源使用 enum（`TaskStatus`, `TaskSource`）
- FastAPI 以 JSON body 為主，已有 `BaseModel` 定義

### Integration Points
- `api_server.py` 為 API server 主入口
- 佇列與狀態在 `pipeline/queue` 中統一管理

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-api*
*Context gathered: 2026-03-21*

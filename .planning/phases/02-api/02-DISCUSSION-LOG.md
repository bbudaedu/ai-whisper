# Phase 2: 對外 API 與認證 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-21
**Phase:** 02-對外 API 與認證
**Areas discussed:** 認證與權限模型, 任務建立介面, 取消語意, 結果下載策略

---

## 認證與權限模型

| Option | Description | Selected |
|--------|-------------|----------|
| API key 交換 JWT | 客戶端先帶長期 API key 換短期 JWT | ✓ |
| 帳密登入換 JWT | 以 email/password 登入 | |
| Google OAuth 換 JWT | OAuth 完成後由後端簽 JWT | |

**User's choice:** API key 交換 JWT
**Notes:** JWT 短效 + refresh token；internal/external 角色區分；Authorization: Bearer；token 欄位 user_id/role/exp；API key/refresh token DB 持久化；internal 可查全部、external 僅自己的。

---

## 任務建立介面

| Option | Description | Selected |
|--------|-------------|----------|
| 單一端點 + type 欄位 | POST /api/tasks，type=upload|youtube | ✓ |
| 拆成兩個端點 | /api/tasks/upload 與 /api/tasks/youtube | |
| 沿用 /api/task action | action-based | |

**User's choice:** 單一端點 + type
**Notes:** 必填 type+source+payload+requester；回應 task_id/status/created_at；upload 用 multipart；YouTube payload url + optional playlist_id；狀態集合 queued/pending/running/done/failed/canceled；支援多格式輸出選擇。

---

## 取消語意

| Option | Description | Selected |
|--------|-------------|----------|
| pending/queued 可取消 | running 不可取消 | ✓ |
| running 也可取消 | 中止進行中 | |
| 僅 queued | pending 也不可取消 | |

**User's choice:** pending/queued 可取消
**Notes:** canceled + reason=client_cancel；同步立即回應；不刪檔；不可取消回 reason code；回應 200 OK + 狀態/原因。

---

## 結果下載策略

| Option | Description | Selected |
|--------|-------------|----------|
| 單一端點打包 ZIP | 一次下載多格式 | ✓ |
| 多端點逐一下載 | 各格式獨立 | |
| 回傳清單 + URL | 先列檔再挑 | |

**User's choice:** 單一端點打包 ZIP
**Notes:** 檔名 task_id+timestamp；Phase 2 不提供原始音檔；Phase 2 不支援單格式下載；下載權限同任務權限。

---

## Claude's Discretion

- 無

## Deferred Ideas

- 無

# Phase 3: 外部 Web UI 與提交流程 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-22
**Phase:** 3-外部 Web UI 與提交流程
**Areas discussed:** 導覽與版面結構、登入與帳戶體驗、任務提交與參數設定、播放清單追蹤與任務追蹤/下載

---

## 導覽與版面結構

| Option | Description | Selected |
|--------|-------------|----------|
| 桌機 Sidebar + 行動版底部 Tab | 延用內部 UI 風格，mobile-first 最易操作 | ✓ |
| 頂部 Tab Bar | 單層 tab，擴充性較低 | |
| 單頁長捲動 | 行動版切換成本高 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 登入後進 Dashboard | 先看總覽再操作 | ✓ |
| 登入後進新增任務 | 直接進入主要動作 | |
| 登入後進播放清單 | 聚焦追蹤管理 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 多頁面分區 | Dashboard/提交/追蹤/播放清單/設定 | ✓ |
| 合併提交+追蹤 | 減少頁面數但易塞滿 | |
| 單頁多區塊 | 行動版可用性差 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 沿用現有卡片風格 + dark mode | 與現有 web-ui 一致 | ✓ |
| 全新極簡單色系 | 品牌改版成本高 | |
| 不支援 dark mode | 省事但體驗較弱 | |

**User's choice:** Auto — recommended defaults selected
**Notes:** [auto] 導覽/版型採用既有內部 UI 風格並優先 mobile-first

---

## 登入與帳戶體驗

| Option | Description | Selected |
|--------|-------------|----------|
| Email/Password + Google OAuth | 滿足需求且使用彈性高 | ✓ |
| 只支援 Email/Password | 實作較簡單 | |
| 只支援 Google OAuth | 入門快但限制大 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 不開放公開註冊 | 由內部建立帳號 | ✓ |
| 自助註冊 + Email 驗證 | 對外開放 | |
| 申請入口 | 填表後審核 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 登入狀態可持續 | 跨刷新維持 | ✓ |
| 關閉瀏覽器即失效 | 安全但不便 | |
| 只限分頁 | 體驗差 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 設定頁統一 Email 通知 | 全域收件人 | ✓ |
| 每任務設定 Email | 彈性高但複雜 | |
| 不做 Email 通知 | 不符需求 | |

**User's choice:** Auto — recommended defaults selected
**Notes:** [auto] 採最小可用登入與通知設定

---

## 任務提交與參數設定

| Option | Description | Selected |
|--------|-------------|----------|
| 單一提交頁 (Upload/YouTube) | 清晰、切換容易 | ✓ |
| 分開兩頁 | 導覽成本高 | |
| 小彈窗快速建立 | 參數難放 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 音檔性質下拉 + Prompt 預設可改 | 滿足 PROC-06/07 | ✓ |
| 只給 Prompt | 使用者負擔高 | |
| 固定預設不可改 | 需求不足 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 多選勾選格式（預設全選） | 滿足 NOTF-02 | ✓ |
| 單選格式 | 不符合多格式需求 | |
| 固定全部 | 無彈性 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 單一 URL 自動偵測 | 可辨識 playlist/單片 | ✓ |
| 分欄位輸入 | 操作步驟多 | |
| 只支援 playlist | 限制過多 | |

**User's choice:** Auto — recommended defaults selected
**Notes:** [auto] 提交流程以單一表單涵蓋需求

---

## 播放清單追蹤與任務追蹤/下載

| Option | Description | Selected |
|--------|-------------|----------|
| 播放清單可新增/啟停/刪除 + 狀態列表 | 完整管理介面 | ✓ |
| 只支援新增/停用 | 管理能力不足 | |
| 僅追蹤不管理 | 不符 UI-04 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 表格清單 + 狀態 badge/步驟 | 可讀性高 | ✓ |
| 卡片式追蹤 | 密度不足 | |
| 僅摘要 | 不足以追蹤 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 10 秒輪詢 + 手動刷新 | 與現有 UI 一致 | ✓ |
| 僅手動刷新 | 即時性不足 | |
| WebSocket 即時推播 | 成本高 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 下載全部(Zip) + 格式清單 | 符合多格式需求 | ✓ |
| 只提供 Zip | 可行但不清楚格式 | |
| 每格式單獨下載 | 需要更多 API | |

**User's choice:** Auto — recommended defaults selected
**Notes:** [auto] 追蹤與下載以清單 + Zip 為主

---

## Claude's Discretion

- Loading skeleton、空狀態插圖與文案
- 視覺間距、字級與 icon 分配
- 錯誤提示文案與顯示位置

## Deferred Ideas

- 公開自助註冊 + Email 驗證
- WebSocket 即時推播
- 任務清單進階搜尋/篩選
- 播放清單完結自動停止追蹤（ENH-05）

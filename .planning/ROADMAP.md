# Roadmap: FaYin v2.0

## Milestones

- [x] **v1.0 (2026-03-24)**: [Milestone v1.0 Archive](milestones/v1.0-ROADMAP.md) - Task Queue, API, Mobile-first Web UI, History.
- [ ] **v2.0 (2026-04-15)**: **全系統自動化 E2E 測試與穩定性增強** - API, Pipeline, Web UI E2E 測試, 說話者名稱編輯, 真實 LLM 串接.

---

## Phases

### Phase 07: 測試基礎設施與 API/Pipeline 自動化 (Test Infrastructure)
建立測試環境（Playwright/Pytest），並完成後端 API 與處理管線的自動化驗證。
**Plans:** 3/3 plans complete
- [x] 07-01-PLAN.md — 建立測試用資料庫、test_config.json 與測試資產目錄。
- [x] 07-02-PLAN.md — 實作 pytest 的後端測試（Auth, Task CRUD, Download）。
- [x] 07-03-PLAN.md — 實作 Pipeline 整合測試（Mock GPU 處理、並發爭搶驗證）。

### Phase 08: Web UI E2E 自動化測試 (UI E2E)
建立 Playwright 測試框架，並完成 External Web UI 的核心流程驗證（Auth, Task, Responsive）。
**Plans:** 2/2 plans complete
- [x] 08-01-PLAN.md — 建立 Playwright 基礎設施與實作登入流程 E2E 測試。
- [x] 08-02-PLAN.md — 實作任務提交、追蹤、狀態更新與響應式佈局 E2E 測試。

### Phase 09: 說話者名稱編輯與真實 LLM 串接 (Refinement)
擴充 v1.0 功能，支援真實人名標註與 OpenAI/Anthropic API 整合。
**Plans:** 1/3 plans executed
- [x] 09-01-PLAN.md — 擴充 API 與資料庫以支援 speaker_name 欄位與編輯端點。
- [ ] 09-02-PLAN.md — 更新 UI 支援在歷史記錄中編輯說話者人名。
- [ ] 09-03-PLAN.md — 優化 AI 校對 Prompt 並串接真實 LLM。

---
*Roadmap updated: 2026-03-28 — 09-01~03 plans created (Refinement)*

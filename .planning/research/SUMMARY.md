# Project Research Summary

**Project:** FaYin
**Domain:** 語音處理平台（Whisper-based transcription + API + 外部 Web UI）
**Researched:** 2026-03-21
**Confidence:** MEDIUM

## Executive Summary

FaYin 是一個以 Whisper 為核心的語音處理平台，目標是把既有的下載→轉錄→校對→排版流程 API 化，並提供外部使用者的 Web UI。在此類產品中，業界標準作法是將 API 與長任務分離，以可持久化的任務佇列與狀態機驅動 pipeline，並用單 GPU 排程與優先權規則保護內部流程。

研究建議採用 FastAPI + Celery/Redis + PostgreSQL 的非同步架構，將現有腳本封裝成可重入的 worker，並建立 Task Registry、Priority Queue、Scheduler/State Machine 等核心元件。對外能力先聚焦在檔案/連結提交、任務狀態查詢、下載與通知，外部 UI 採用 React + Vite + React Query 的 API 驅動模式，確保 mobile-first 且可用於長任務追蹤。

關鍵風險集中在「把長任務塞進 API 進程」、「單 GPU 排程失效」、「任務狀態機不完整」與「多租戶隔離不足」。對策是：強制佇列化與持久化狀態、GPU single-flight lock 搭配心跳/超時釋放、階段式狀態機與冪等邏輯、以及以 tenant scope 與短效簽名 URL 強化授權。行動端上傳需支援 resumable/chunked 上傳，避免長音檔因網路不穩反覆重傳。

## Key Findings

### Recommended Stack

技術棧以成熟的 FastAPI 生態為核心，後端採用 async ORM 與正式任務佇列，前端沿用 React 19 + Vite 的現有方向，並配套資料快取、表單與驗證工具。版本相容性需注意 FastAPI 與 Pydantic v2、以及 React/React DOM 版本一致性。

**Core technologies:**
- **FastAPI 0.135.1**：後端 API 框架 — 與 Pydantic v2 整合成熟，適合 ASGI。
- **Uvicorn 0.41.0**：ASGI 伺服器 — FastAPI 標準部署組合。
- **Pydantic 2.12.5**：資料驗證/序列化 — 型別一致性與效能佳。
- **PostgreSQL 17.9 + SQLAlchemy 2.0.48 + Alembic 1.18.4**：任務/權限/審計資料 — 可持久化與可遷移。
- **Celery 5.6.2 + Redis 8.6.1**：任務佇列與排程 — 支援優先級與重試，符合單 GPU。
- **asyncpg 0.31.0**：PostgreSQL async driver — 與 SQLAlchemy async 搭配。
- **pyannote-audio 4.0.4**：speaker diarization — 主流方案，支援 A/B/C/D。
- **Authlib 1.6.9 + PyJWT 2.12.1 + argon2-cffi 25.1.0**：OAuth/JWT/密碼雜湊 — 外部認證核心。
- **boto3 1.42.72**：S3 物件儲存 — 便於擴展與長期保存。
- **React 19.2.4 + Vite 8.0.1 + react-router-dom 7.13.1**：外部 Web UI 核心框架。
- **@tanstack/react-query 5.91.3 + zod 4.3.6 + react-hook-form 7.71.2**：API 查詢、表單與驗證。

### Expected Features

MVP 需涵蓋完整的「提交→排程→轉錄→下載」最短路徑，並提供外部使用者可追蹤的任務體驗；差異化功能建議在驗證後增補。

**Must have (table stakes):**
- 音檔/連結提交（含 YouTube 連結） — 產品入口
- 非同步任務佇列 + 狀態查詢/取消 — 長任務必備
- 基礎轉錄品質（標點、ITN） — 可讀性核心
- 說話者分離（A/B/C/D） — 多人內容需求
- 時間戳與多格式輸出（txt/srt/docx/pdf 等） — 使用情境覆蓋
- 基礎通知（Email/Webhook） — 完成後通知
- 認證與存取控制 — 外部 API/UI 必備

**Should have (competitive):**
- 上傳講義/文件輔助校對 — 提升特定領域正確率
- 自動摘要/重點整理 — 快速消化內容
- YouTube 播放清單自動監控 — 工作流差異化
- 協作與批註 — 使用者規模擴大後提升效率

**Defer (v2+):**
- 說話者名稱辨識 — 需名稱資料庫與高準確率
- 即時串流轉錄 — 架構成本高
- 多 GPU 併行排程 — 成本與複雜度高
- 內建計費/訂閱系統 — 需營運與法規配套

### Architecture Approach

建議採分層架構：API 僅負責建立任務與查詢狀態，排程與狀態機獨立，worker 以階段式交接運作，並透過持久化 Task Registry 與 GPU single-flight lock 確保可重試與資源穩定。既有腳本應以 wrapper/adapter 方式接入，避免破壞內部流程。

**Major components:**
1. **API Layer** — 認證、任務建立/查詢/取消、上傳/下載、通知。
2. **Task Registry + Priority Queue** — 任務狀態與優先權管理。
3. **Scheduler/State Machine** — pipeline 階段流轉與重試。
4. **Workers（download/transcribe/proofread/format）** — 單職責、可獨立擴展。
5. **Storage** — 音檔/輸出永久保存與下載。

### Critical Pitfalls

1. **API 進程/BackgroundTasks 跑長任務** — 必須使用正式 task queue，API 只建立任務並查詢狀態。
2. **單 GPU 排程失效** — 需要集中式排程器、內外優先級規則與 GPU lock 心跳/超時。
3. **任務狀態機不完整** — 採階段式狀態機與冪等重試，避免重複輸出或漏步驟。
4. **多租戶隔離不足** — 任務與檔案需 tenant scope，下載使用短效簽名 URL。
5. **Mobile 上傳失敗** — 必須支援 resumable/chunked upload 與完整性檢查。

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: 任務佇列與狀態機基礎
**Rationale:** 所有外部能力依賴可持久化任務與穩定 GPU 排程，且需避免長任務阻塞 API。
**Delivers:** Task Registry、Priority Queue、Scheduler/State Machine、worker wrapper、GPU lock 與內部流程回歸保護。
**Addresses:** 非同步任務佇列 + 狀態查詢/取消、基礎轉錄 pipeline。
**Avoids:** Pitfall 1、2、3、9。

### Phase 2: 外部 API + 認證/授權 + 多租戶隔離
**Rationale:** 在 pipeline 穩定後再開放外部存取，避免資安與資料外洩風險。
**Delivers:** OAuth/Email 登入、tenant scope、短效簽名下載、審計日誌。
**Addresses:** 認證與存取控制、API 對外化。
**Avoids:** Pitfall 4、Security mistakes（可猜測 ID / 永久連結）。

### Phase 3: External Web UI + 上傳流程（mobile-first）
**Rationale:** UI 需依賴穩定 API 與權限模型，且上傳流程是行動端成敗關鍵。
**Delivers:** Mobile-first UI、任務追蹤、分段/續傳上傳、YouTube 連結提交、通知設定。
**Addresses:** 音檔/連結提交、任務進度追蹤、Email/Webhook 通知。
**Avoids:** Pitfall 5、UX pitfalls（單一進度條、無 ETA）。

### Phase 4: 轉錄品質與處理增強
**Rationale:** 基礎流程穩定後再優化品質，避免邊界錯誤與 diarization 期望落差。
**Delivers:** chunk/VAD 策略、時間戳校正、diarization 穩定化、講義輔助校對。
**Addresses:** 基礎轉錄品質、說話者分離、時間戳、校對增強。
**Avoids:** Pitfall 6、7、Prompt injection 風險。

### Phase 5: 儲存與長期營運
**Rationale:** 永久保存會快速放大儲存成本，需在用量成長前建立策略。
**Delivers:** 分層儲存、索引策略、容量監控與擴容流程。
**Addresses:** 永久保存、長期下載可用性。
**Avoids:** Pitfall 8。

### Phase Ordering Rationale

- 佇列/狀態機是所有功能依賴的核心，必須先完成。
- 認證與多租戶隔離是對外開放前的門檻。
- UI 與上傳流程依賴 API 穩定性，且 mobile-first 需額外處理續傳。
- 品質調校與長期儲存屬於穩定後的優化與營運層。

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** resumable/chunked upload 實作與 S3/本地儲存策略選型。
- **Phase 4:** 長音檔 chunk/VAD 參數基準、diarization 期望管理與提示注入防護。
- **Phase 5:** 儲存分層與成本模型、保留政策設計。

Phases with standard patterns (skip research-phase):
- **Phase 1:** Celery/Redis + DB state machine 的典型模式明確。
- **Phase 2:** OAuth/JWT/tenant scope 為成熟的 API 安全模式。

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | 多數來自官方套件/版本資訊，但選型仍需依部署限制驗證。 |
| Features | MEDIUM | 參照競品與現有需求，需再由實際用戶驗證優先序。 |
| Architecture | MEDIUM | 以現有專案架構推導，缺外部權威來源。 |
| Pitfalls | MEDIUM | 部分有官方文件支撐，但仍需在專案實測驗證。 |

**Overall confidence:** MEDIUM

### Gaps to Address

- **上傳續傳/分段方案選型**：需評估 S3 presigned 上傳或 server 代理方案的成本與風險。
- **長音檔品質基準**：需建立實際資料集與回歸測試，驗證 chunk/VAD 參數。
- **儲存與保留策略**：需明確資料保存期限、分層策略與成本預估。
- **LLM 校對安全性**：講義上傳可能引入 prompt injection，需要隔離與清理策略。

## Sources

### Primary (HIGH confidence)
- https://fastapi.tiangolo.com/tutorial/background-tasks/ — 長任務不建議放在 BackgroundTasks
- https://huggingface.co/openai/whisper-large/blob/main/README.md — 長音檔 chunk 與幻覺風險
- https://docs.pyannote.ai/tutorials/speaker-configuration — speaker diarization 參數與重疊處理
- https://docs.cloud.google.com/storage/docs/resumable-uploads — 可續傳/offset 上傳機制

### Secondary (MEDIUM confidence)
- https://docs.rev.ai/api/features/ — 轉錄品質與 ITN 參考
- https://otter.ai/features — 競品功能與協作特性
- https://developers.deepgram.com/docs/summarization — 自動摘要能力
- https://www.assemblyai.com/blog/assemblyai-speaker-identification-diarization — speaker identification 依賴 diarization

### Tertiary (LOW confidence)
- /home/budaedu/ai-whisper/.planning/PROJECT.md — 內部現況與需求描述

---
*Research completed: 2026-03-21*
*Ready for roadmap: yes*

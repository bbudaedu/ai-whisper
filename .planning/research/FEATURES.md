# Feature Research

**Domain:** 語音處理 / 轉錄平台（Speech Processing & Transcription）
**Researched:** 2026-03-21
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 音檔/連結提交（檔案上傳、YouTube 連結） | 轉錄平台的基本入口 | MEDIUM | 需處理多格式媒體、大小限制與失敗重試 |
| 非同步任務與狀態查詢 | 長音檔需要佇列與可追蹤狀態 | MEDIUM | API 必備能力（提交、查詢、取消、下載） |
| 基礎轉錄品質（自動標點、數字/日期正規化） | 現代轉錄產品預期輸出可直接閱讀 | MEDIUM | Rev AI 提供 punctuation 與 ITN（inverse text normalization）能力 |
| 說話者分離（Speaker diarization/labels） | 會議與多人內容常態需求 | MEDIUM | Rev AI/Deepgram 均提供 diarization；v1 可先用 A/B/C/D |
| 時間戳（word/utterance timestamps） | 轉錄對齊、字幕與回放常見需求 | MEDIUM | Rev AI/Deepgram 皆支援 timestamps |
| 多格式輸出（TXT/SRT/DOCX/PDF 等） | 不同使用情境需要不同格式 | LOW | Otter 方案列出多種匯出格式 |
| 基礎通知（Email/Webhook） | 非同步任務完成需通知 | LOW | 尤其是 API/批次用戶 |
| 認證與存取控制 | 對外 API/UI 的必備安全需求 | MEDIUM | 與多租戶資料隔離相依 |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 上傳講義/文件輔助校對（Domain-adapted proofreading） | 專有語料提升正確率與可讀性 | MEDIUM | 對佛學課程/會議紀錄價值高 |
| 說話者「名稱」辨識（Speaker identification by name） | 直接輸出人名，省去手動標註 | HIGH | Otter 提供 speaker identification；AssemblyAI 需先 diarization 再 identification |
| 自動摘要/重點整理 | 快速產出可消化內容 | MEDIUM | Deepgram 提供 summarization 功能，可作為差異化 |
| YouTube 播放清單自動監控 | 對內容工作流更順暢 | MEDIUM | 對教學/系列內容具優勢 |
| 協作與批註（共享、留言） | 多人整理與審閱效率提升 | MEDIUM | Otter 以分享與評論做協作亮點 |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 即時串流轉錄 | 看似更即時 | 架構成本高、GPU 競爭、延遲與準確率難平衡 | 先做高品質非同步轉錄與通知 |
| 多 GPU 併行排程 | 追求吞吐量 | 成本與排程複雜度暴增，與單 GPU 資源不符 | 單 GPU 嚴格佇列 + 任務優先級 |
| 內建計費/訂閱系統 | 想快速商業化 | 需要合規、稅務與客服配套 | 先以手動帳務或白名單方案 |
| 以人名為核心的自動識別 v1 | 追求「完整標註」 | 名稱資料蒐集與隱私風險高，識別錯誤成本大 | 先用 A/B/C/D + 手動對應 |

## Feature Dependencies

```
音檔/連結提交
    └──requires──> 非同步任務與狀態查詢
                       └──requires──> 基礎轉錄品質
                                      └──requires──> 時間戳與輸出格式

說話者分離（Diarization）
    └──enhances──> 基礎轉錄品質
    └──requires──> 基礎轉錄品質

說話者名稱辨識（Identification）
    └──requires──> 說話者分離（Diarization）

通知（Email/Webhook）
    └──requires──> 非同步任務與狀態查詢

協作與批註
    └──requires──> 結果保存與權限控管
```

### Dependency Notes

- **說話者名稱辨識 requires 說話者分離：** AssemblyAI 指出 identification 需先有 speaker labels。
- **通知 requires 非同步任務與狀態查詢：** 必須能判斷完成/失敗狀態。
- **協作與批註 requires 結果保存與權限控管：** 需要長期儲存與多使用者存取。

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] 檔案/連結提交（含 YouTube 連結） — 產品入口
- [ ] 非同步任務佇列 + 狀態查詢/取消 — 長音檔必備
- [ ] 基礎轉錄品質（標點、ITN） — 可讀性與可用性
- [ ] 說話者分離 A/B/C/D — 會議與課程基本需求
- [ ] 多格式輸出（txt, srt, docx/pdf） — 使用情境覆蓋
- [ ] Email/Webhook 通知 — 非同步完成的核心體驗
- [ ] 外部 API + Mobile-first Web UI + 認證 — 對外使用必要

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] 自動摘要/重點整理 — 使用者開始需要快速消化時
- [ ] Custom vocabulary/詞彙表 — 頻繁遇到專有名詞時
- [ ] Disfluency/Profanity filtering — 有明確合規需求時
- [ ] 協作與批註 — 使用者規模擴大後

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] 說話者名稱辨識（自動人名） — 需要名稱資料庫與高準確率
- [ ] 即時串流轉錄 — 架構成本高
- [ ] 多 GPU 併行排程 — 成本與排程複雜度高
- [ ] 內建計費/訂閱 — 需營運與法規配套

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 檔案/連結提交 | HIGH | MEDIUM | P1 |
| 非同步任務佇列 + 狀態查詢 | HIGH | MEDIUM | P1 |
| 說話者分離（A/B/C/D） | HIGH | MEDIUM | P1 |
| 多格式輸出 | HIGH | LOW | P1 |
| Email/Webhook 通知 | MEDIUM | LOW | P1 |
| 自動摘要/重點整理 | MEDIUM | MEDIUM | P2 |
| Custom vocabulary | MEDIUM | MEDIUM | P2 |
| 協作與批註 | MEDIUM | MEDIUM | P2 |
| 說話者名稱辨識 | HIGH | HIGH | P3 |
| 即時串流轉錄 | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A (Otter.ai) | Competitor B (Rev AI) | Our Approach |
|---------|--------------------------|------------------------|--------------|
| 說話者標註 | 提供 speaker identification by name | 提供 speaker diarization（非 identification） | v1 先 A/B/C/D，後續再做名稱辨識 |
| 多格式輸出 | mp3/txt/pdf/docx/srt 等 | API 以結構化輸出為主 | 保留 txt/srt/json/docx/pdf |
| 轉錄品質增強 | 會議摘要、關鍵字等 | punctuation、ITN、disfluency、profanity | 先做標點/ITN，視需求補過濾與摘要 |

## Sources

- https://docs.rev.ai/api/features/
- https://docs.rev.ai/faq/
- https://otter.ai/features
- https://otter.ai/pricing-2025
- https://developers.deepgram.com/docs/summarization
- https://developers.deepgram.com/docs/stt-intelligence-feature-overview
- https://deepgram.com/learn/working-with-timestamps-utterances-and-speaker-diarization-in-deepgram
- https://www.assemblyai.com/blog/assemblyai-speaker-identification-diarization

---
*Feature research for: 語音處理 / 轉錄平台*
*Researched: 2026-03-21*

# Pitfalls Research

**Domain:** 語音處理平台（Whisper 轉錄 + 外部 API + Client Web UI + 單 GPU 排程）
**Researched:** 2026-03-21
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: 用 FastAPI BackgroundTasks 或同步請求跑長任務

**What goes wrong:**
把轉錄/校對/排版塞在 API 進程或 BackgroundTasks，造成請求逾時、重啟即丟任務、佇列無法擴展。

**Why it happens:**
內部工具習慣直接呼叫腳本，外部 API 化時沿用同一流程，忽略長任務需要獨立 worker 與佇列。

**How to avoid:**
採用正式 task queue（如 Celery/RQ），轉錄與校對在 worker 執行；API 只負責建立任務與查詢狀態；狀態持久化（DB/Redis）+ 重試策略。

**Warning signs:**
- API latency 飆升或 504/timeout
- 服務重啟後任務消失
- 同時多任務時 CPU/GPU 使用率不穩定

**Phase to address:**
Phase 1 — 任務佇列與 GPU 排程基礎

---

### Pitfall 2: 單 GPU 排程失效（優先權倒掛或資源鎖死）

**What goes wrong:**
外部任務壓垮內部任務；GPU lock 無法釋放；或 I/O 任務也被 GPU 鎖住導致整體吞吐下降。

**Why it happens:**
沒有集中式排程器；優先權只在 UI 層面，worker 不知道內外優先；GPU lock 邏輯與任務狀態不同步。

**How to avoid:**
建立單一任務佇列 + 排程器，明確區分「GPU-bound」與「CPU/I/O-bound」階段；內部任務優先權寫入排程規則；GPU 鎖有心跳與超時釋放。

**Warning signs:**
- 內部任務等待時間 > 既定 SLA
- GPU 閒置但隊列不動
- GPU lock 檔案長時間存在

**Phase to address:**
Phase 1 — 任務佇列與 GPU 排程基礎

---

### Pitfall 3: 任務狀態機不完整（重試造成重複輸出或漏步驟）

**What goes wrong:**
同一音檔被重複處理；下游步驟在上游尚未完成時就啟動；取消任務後仍繼續跑。

**Why it happens:**
用「單一 status 欄位」代表整條 pipeline，缺少狀態機與 idempotency；重試只靠「重新跑」。

**How to avoid:**
明確的 pipeline state machine（download → transcribe → proofread → format），每步驟具備可重入與冪等（idempotent）判斷；取消/失敗流程有補償邏輯。

**Warning signs:**
- 同一任務出現多份輸出
- 佇列中大量「卡在某一步驟」
- Cancel 後仍產生結果

**Phase to address:**
Phase 1 — 任務佇列與 GPU 排程基礎

---

### Pitfall 4: 外部 API/多租戶隔離不足（檔案可被跨租戶存取）

**What goes wrong:**
外部使用者可透過猜測 ID 下載他人音檔或成果；內部與外部資料混用，權限不清。

**Why it happens:**
內部工具假設可信使用者；外部 API 化後未建立 tenant 分層與授權規則。

**How to avoid:**
資料模型加入 tenant/user scope；所有下載連結使用短效簽名 URL 或授權檢查；API 端點強制驗證；紀錄存取稽核。

**Warning signs:**
- 下載 API 只用任務 ID 當授權
- 日誌出現非本人檔案下載
- 外部 UI 無明確使用者隔離

**Phase to address:**
Phase 2 — 外部 API 與認證/授權

---

### Pitfall 5: Mobile 上傳失敗（無續傳/分段導致大量重傳）

**What goes wrong:**
長音檔在手機或不穩定網路下頻繁中斷，使用者必須從頭上傳，造成流失。

**Why it happens:**
沿用內部環境的單次上傳流程，忽略行動網路不穩與大檔案。

**How to avoid:**
採用 resumable/chunked upload，保存 upload session 與 offset；上傳完成後做完整性檢查；在 UI 顯示可續傳狀態。

**Warning signs:**
- 上傳失敗率高
- 使用者抱怨「上傳到一半重來」
- 大檔案上傳時間極不穩定

**Phase to address:**
Phase 3 — Client Web UI 與上傳流程

---

### Pitfall 6: 長音檔分段/VAD 設定不當，造成漏字或重複內容

**What goes wrong:**
邊界處遺漏、斷句錯誤、重複片段，或 Whisper 產生不在音檔中的文字（hallucinations）。

**Why it happens:**
未針對長音檔做分段策略與 VAD 參數驗證；只用預設值上線。

**How to avoid:**
依音檔型態（會議/課程）調整 chunk 與 VAD；對邊界做對齊與拼接驗證；建立基準集做回歸測試。

**Warning signs:**
- 轉錄結果出現明顯重複段落
- 句子在檔案中消失
- 用戶回報「模型在亂講」

**Phase to address:**
Phase 4 — 轉錄品質與長音檔策略

---

### Pitfall 7: Speaker diarization 期望過高（未設定 speaker 數或重疊語音處理）

**What goes wrong:**
A/B/C 標註頻繁跳動或錯置，使用者誤解為「精準辨識」，造成信任崩壞。

**Why it happens:**
把 diarization 當成「辨識人名」；未依場景設定 speaker 數或重疊語音策略。

**How to avoid:**
已知 speaker 數時明確設定；需要非重疊輸出就用 exclusive 模式；對不同錄音品質建立適用/不適用條件與 UI 說明。

**Warning signs:**
- 同一句話被拆成多個 speaker
- Speaker label 在短時間內頻繁切換
- 使用者回報「標註不可信」

**Phase to address:**
Phase 4 — 轉錄品質與 Speaker diarization

---

### Pitfall 8: 永久保存導致儲存/索引成本爆炸

**What goes wrong:**
音檔與輸出永久保存，磁碟快速成長、查詢變慢、備份與災難復原成本上升。

**Why it happens:**
「永久保存」只定義政策，不設計儲存分層、索引與清理策略。

**How to avoid:**
分層儲存（熱/冷）、壓縮與去重；資料目錄與索引分離；建立容量監控與擴充計畫。

**Warning signs:**
- 儲存使用率成長無預警
- 下載/查詢延遲逐月上升
- 備份時間越來越長

**Phase to address:**
Phase 5 — 儲存與長期營運

---

### Pitfall 9: 對既有內部流程造成回歸

**What goes wrong:**
新 API/佇列改動導致內部 YouTube 監控或自動校對失效，影響既有產出。

**Why it happens:**
共用設定與排程邏輯，缺少回歸測試與 feature flag。

**How to avoid:**
保留既有流程的執行路徑；新增功能以 feature flag 切換；建立內部流程的回歸測試與健康檢查。

**Warning signs:**
- 內部任務成功率下降
- 監控看板出現「卡住」狀態
- 產出檔案品質突然改變

**Phase to address:**
Phase 1–2（API 化與佇列化）

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| 任務狀態只存在記憶體 | 快速上線 | 重啟即丟任務、無法重試 | MVP 也不建議 |
| 上傳僅支援單次 POST | 實作最省時 | Mobile 失敗率高、客服成本爆 | 只有內部小檔案時 |
| 音檔/輸出未做 tenant 分層 | 目錄簡單 | 資安風險、無法擴展權限 | Never |
| 轉錄結果直接覆寫 | 邏輯簡單 | 追溯困難、無法審核 | 只在內測 |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Google OAuth | Redirect URI/Origin 未包含所有環境 | 明確列出 dev/staging/prod 並驗證回呼 |
| Webhook | 只送一次、不驗證簽章 | 設計重試、簽章驗證與去重 |
| Email 通知 | 不處理退信或被標記為垃圾郵件 | 設定 SPF/DKIM/DMARC、追蹤送達率 |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| API 進程直接執行轉錄 | API timeout、CPU/GPU 資源耗盡 | worker 分離 + queue | 併發 > 2–3 任務 |
| I/O 任務佔用 GPU 鎖 | GPU 低利用率 | GPU 鎖只包覆轉錄步驟 | 任何大量下載/轉檔時 |
| 大檔案上傳未限速 | 網路壓垮、其他請求延遲 | 分段 + 速率限制 + 背壓 | 併發 > 5–10 上傳 |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| 下載連結永久有效 | 外洩長期可被存取 | 短效簽名 URL + 授權檢查 |
| 任務 ID 可猜測 | 任意存取他人檔案 | 使用不可預測 ID + tenant 驗證 |
| 上傳講義/文本直接進 LLM 提示詞 | Prompt injection 影響輸出 | 內容隔離、指令白名單、清理提示詞 |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 只顯示單一進度條 | 不知道是在上傳還是轉錄 | 區分 upload/queue/transcribe/proofread/format |
| 無佇列位置或 ETA | 使用者焦慮、重複提交 | 顯示隊列位置與預估時間 |
| Speaker A/B/C 未解釋 | 誤以為是姓名 | UI 明確標註「僅分群、非人名」 |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **任務佇列：** 常缺少持久化狀態 — 驗證重啟後任務可恢復
- [ ] **檔案上傳：** 常缺少續傳與完整性檢查 — 驗證中斷後可續傳
- [ ] **完成通知：** 常缺少重試與退信處理 — 驗證通知失敗可重送
- [ ] **取消任務：** 常缺少實際停止 GPU 工作 — 驗證取消後 GPU 不再執行

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| 任務丟失 | MEDIUM | 從持久化狀態重建任務；對失敗任務批次重排 |
| GPU lock 卡死 | LOW | 釋放 lock、重啟 worker、補寫保護性 timeout |
| 儲存空間不足 | HIGH | 暫停新上傳、搬移到冷儲存、擴容 |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| BackgroundTasks 跑長任務 | Phase 1 | 任務重啟後可繼續、API 無 timeout |
| 單 GPU 排程失效 | Phase 1 | 內部任務 SLA 維持、GPU 使用率穩定 |
| 任務狀態機不完整 | Phase 1 | 重試不重複、取消即停止 |
| 多租戶隔離不足 | Phase 2 | 用戶無法存取他人檔案 |
| Mobile 上傳失敗 | Phase 3 | 中斷可續傳，成功率提升 |
| 長音檔分段/VAD 問題 | Phase 4 | 边界漏字/重複顯著降低 |
| Speaker diarization 期望過高 | Phase 4 | 標註穩定、錯置率下降 |
| 永久保存成本爆炸 | Phase 5 | 容量/成本可預測且有告警 |
| 內部流程回歸 | Phase 1–2 | 既有流程健康檢查通過 |

## Sources

- FastAPI Background Tasks Caveat（長任務建議使用 Celery/queue）: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Whisper model README（長音檔 chunking、幻覺與重複風險）: https://huggingface.co/openai/whisper-large/blob/main/README.md
- pyannote speaker configuration（speaker 數設定與重疊處理）: https://docs.pyannote.ai/tutorials/speaker-configuration
- Google Cloud Storage Resumable Uploads（可續傳/offset 機制）: https://docs.cloud.google.com/storage/docs/resumable-uploads

---
*Pitfalls research for: 語音處理平台（FaYin）*
*Researched: 2026-03-21*

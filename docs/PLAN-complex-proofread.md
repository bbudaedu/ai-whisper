# 專案實作計畫：自訂校對提示詞與複雜語音架構設計 

## 1. 任務目標
1. **完善前端 UI**：自動載入預設的校對 Prompt 給使用者在 UI 上修改。
2. **打通後端 Pipeline**：確保使用者自訂的校對提示詞能正確傳遞並取代預設版，交由 Gemini 執行校對。
3. **架構最佳實務**：針對複雜語言場景（如多語系混雜、多講者、粵語口音與真言宗咒語等），規劃最佳的系統架構與處理流程。

---

## 2. 複雜語音場景架構規劃 (Architecture Best Practices)

對於單純的 Whisper 模型，碰到「巴利文/緬甸文/中文翻譯（多講者）」或「廣東口音/真言宗咒語（單講者）」極易產生**幻覺 (Hallucinations)** 或是強行翻譯出亂碼。
我們的最佳實務是採用 **「Whisper 引導解碼」 + 「LLM 語境修復與重構」** 的雙層（Dual-Pass）架構。

### 核心處理策略
#### A. 音訊轉錄階段 (Whisper Layer)
- **初始提示詞注入 (`initial_prompt`)**：在播放清單的 Whisper Prompt 中，必須注入與該課程高度相關的名詞。
  - *案例 1*：填入 `莫哥禪法, 長老, 巴利文, 緬甸語, 南傳佛教`。
  - *案例 2*：填入 `真言宗, 悉曇梵文, 嗡阿吽, 廣東話`。
  這能大幅降低模型將陌生語音誤認為噪音或亂譯的機率。
- **語系策略 (`language`)**：若是兩種語言來回交替，建議使用 `auto` 或強制設為 `zh` 讓 Whisper 透過音譯強行輸出文本，再由 LLM 來接手。

#### B. 校對修復階段 (Gemini LLM Layer - 真正的關鍵)
這是為何「自訂 Proofread Prompt」如此重要的原因。我們不需要撰寫極端複雜的程式碼來做語者分離，而是透過這套機制，讓強大的 LLM 理解語境：
- **案例 1 (多講者：長老與翻譯) 的 Prompt 撰寫實務**：
  > "這段演講有兩位講者交替說話。一位是緬甸長老（說緬文/巴利文唱誦），一位是中文翻譯。請以中文翻譯的內容為主軸進行整理，過濾或合理音譯長老的梵音。請將口語贅字去除，並參考講義專有名詞。"
- **案例 2 (口音與咒語) 的 Prompt 撰寫實務**：
  > "講者帶有深厚的香港口音普通話，並夾雜廣東話與真言宗咒語。請將廣東話口語轉為標準中文書面語。對於咒語部分（如嗡阿吽等），請務必保留不作意譯，並參考附加講義。"

#### C. 未來擴充 (進階選項)
若這套 Prompt 工程仍不足，系統架構上預留了 **Speaker Diarization (語者分離) 中介層**。可在 `auto_youtube_whisper.py` 階段整合 `pyannote.audio`，將字幕預先打上 `[Speaker 1]` 和 `[Speaker 2]` 的標籤，再送給 Gemini 判讀。

---

## 3. 系統實作步驟 (Implementation Steps)

### Phase 2 即將指派的 Agent 群組
實作階段預計運用 3 個專門 Agent：`frontend-specialist`、`backend-specialist` 與 `test-engineer`。

### Step 1: 後端與 API 端 (`backend-specialist`)
1. **開放讀取 API**: 在 FastAPI 中新增 `GET /api/default-proofread-prompt` 讓前端能抓取 `skills/buddhist-proofreading/prompts/proofread.md` 的內容。
2. **串接管線 (Pipeline)**: 
   - `playlist_manager.py` 和現有 JSON 結構已支援 `proofread_prompt`。
   - 修改 `auto_youtube_whisper.py` 與 `auto_proofread.py`：讓 `proofread_srt()` 方法接收動態傳入的 custom prompt。若使用者有填寫，則取代預設的 `.md` 檔案邏輯，將客製化指令餵給 Gemini。

### Step 2: 前端 UI 端 (`frontend-specialist`)
1. **狀態管理**: 在 `PlaylistTaskManager.tsx` 的 `<AddPlaylistModal>` 與 `<PlaylistCard>` 編輯模式中，當開啟表單時，向 API 拉取預設的 Prompt。
2. **表單呈現**: 將這些預設文字呈現在 `Textarea` 中，讓使用者在建立清單時就能直接預覽、修改或加上客製化條件（符合上述案例情境）。

### Step 3: 品質控管與測試 (`test-engineer`)
1. **Unit Test API**: 測試 API 是否正常回傳 MD 檔內容。
2. **整合驗證**: 測試存取一組含有自定義 Prompt 的播放清單，驗證 Gemini 生成的結果是否切實遵守了新的 Prompt 規則。

---

## 4. 接下來的動作 (Next Steps)
等待使用者確認本計畫 (Orchestration Phase 1)。確認後，將啟動 Phase 2 進行平行開發與測試。

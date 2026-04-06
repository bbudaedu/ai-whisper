# Requirements: v3.0 (多語言支援、Webhook 與摘要優化)

## 🎯 Goals
擴充平台的核心能力，從「穩定轉錄」進化為「跨國/自動化整合」平台。

## 📋 Scoping Questions
- **多語言範圍**: 是否僅限 UI 國際化 (i18n)，還是包含語音轉譯 (Translation) 功能？
- **Webhook 規格**: 支援哪些事件 (on_done, on_error)？是否需要簽章驗證安全性？
- **摘要引擎**: 使用哪種 LLM (Gemini 2.0/Pro)? 摘要的格式 (條列/摘要/短文) 是否可自訂？

## 🧩 Requirements

### REQ-01: 多語言介面與轉譯 (i18n & Translation)
- [ ] **UI i18n**: 前端 UI 支援繁中/簡中/英文切換。
- [ ] **Translation API**: API 支援設定轉譯目標語言（如日文、韓文）。

### REQ-02: Webhook 通知系統
- [ ] **Event Trigger**: 任務完成或失敗時自動發送 POST 請求至使用者設定的 URL。
- [ ] **Webhook Config**: UI/API 支援設定 Webhook URL 與 Secret。

### REQ-03: 自動摘要功能
- [ ] **Summarization Node**: Pipeline 新增摘要處理階段。
- [ ] **Summary Output**: 提供摘要格式的 txt 與 docx 下載。

## 📝 Traceability

| ID | Requirement | Phase | Status |
|----|-------------|-------|--------|
| REQ-01 | 多語言支援 | TBD | Pending |
| REQ-02 | Webhook 通知 | TBD | Pending |
| REQ-03 | 自動摘要 | TBD | Pending |

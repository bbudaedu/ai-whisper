# 技術棧（Stack）

**Analysis Date:** 2026-03-20

## 語言

- **Python 3.x**：後端服務、pipeline、自動化腳本。
- **TypeScript 5.x**：前端 Web UI（`web-ui/`）。

## 執行環境

- **Python runtime**：後端與 pipeline。
- **Node.js runtime**：前端建置與開發（`web-ui/`）。

## 前端框架與工具

- **React**（`web-ui/package.json`）
- **Vite**（`web-ui/vite.config.ts`）
- **Tailwind CSS**（`web-ui/package.json`）
- **ESLint**（`web-ui/eslint.config.js`）

## 後端與服務入口

- 後端 API 入口：`api_server.py`
- Pipeline 入口：`pipeline/notebooklm_scheduler.py`, `pipeline/notebooklm_tasks.py`
- 自動化入口：`auto_notebooklm.py`, `auto_youtube_whisper.py`

## 依賴與套件管理

- **Python**：使用 `pip`（依賴未集中於單一檔案，需依環境管理）
- **Node.js**：`web-ui/package.json` 與 `web-ui/package-lock.json`

## 設定與配置

- 全域設定：`config.json`（另有備份 `config.json.bak`）
- 其他設定：`model_capabilities.yaml`

## 其他工具

- Shell scripts：`start_dashboard.sh`, `scripts/*.sh`

---

*Stack analysis: 2026-03-20*

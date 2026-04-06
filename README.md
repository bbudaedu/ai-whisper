# AI-Whisper

AI-Whisper 是一個自動化的 AI 語音轉文字與後處理（Post-processing）工作流服務。專案結合了各大開放資源與服務，打造從全自動下載、語音轉錄、校對、摘要，到匯出多元格式（字幕檔、Markdown、心智圖）的完整管線（Pipeline）。該專案採用模組化與微服務（Microservice-like）架構，並且擁有一個 React (TypeScript) 建構的管理儀表板。

## ✨ 核心特色 (Features)

* **全自動影音下載與轉錄 (Auto YouTube Whisper)**
  基於 `yt-dlp` 自動監控與下載影音內容，透過強大的 `faster-whisper` (Large-v3/v2) 利用 GPU 進行高速、高精準度的在地端語音轉文字 (Speech-to-Text)。
* **自動校對與後處理 (AI Proofreading & Post-processing)**
  透過整合 **Google Gemini**（或其他 LLMs）進行字幕文件的智慧校對，包括語意檢查、自動上標點（Punctuation），甚至生成文件摘要、逐字稿 Markdown、資訊圖表解析等後處理工作。
* **NotebookLM 自動化管線 (NotebookLM Scheduler)**
  包含對於 Google NotebookLM 操作的任務排程驅動，將長文本透過自動化機制生成可閱讀的精煉教材及報告。
* **全端管理介面 (Full-stack Dashboard)**
  擁有使用 React 19 與 Vite 打包的 Web UI 儀表板，支援即時查看任務狀態（Pipeline 執行狀況）、重試錯誤任務等。
* **可靠的狀態儲存機制 (Resilient State Management)**
  透過 JSON (如 `processed_videos.json`、`notebooklm_queue.json`) 以及 SQLite (如 `nocturne_memory` 內建機制) 來進行狀態持久化，支援崩潰後重試與背景任務（Background Tasks）處理。
* **SMTP 自動通知機制**
  任務處理完成或需要人工介入時，自動寄送郵件通知管理員。

---

## 🏗 架構概述 (Architecture)

本專案採用 **分離關注點（Separation of Concerns）** 與 **狀態驅動（State-driven）** 演算法來進行管線管理。

1. **Pipeline Layer (`pipeline/`)**: 專案的核心業務邏輯。負責處理具體的工作流節點（抓取影片 -> 轉錄 -> 大語言模型校對 -> 歸檔）。
2. **API Integration Layer**: 將外部 API（對話模型、外部服務平台等）進行隔離封裝，以如 `api_client.py` 提供高可用且具備重試機制的串接。
3. **Backend Services (`auto_*.py`, `api_server.py`)**: 作為各種工作流的實例化入口（Entry Points），FastAPI 提供 RESTful 的路由供前端操作。
4. **Frontend Layer (`web-ui/`)**: 反應迅速的 React 儀表板，管理所有背景非同步任務。
5. **Memory & Persistence (`nocturne_memory/`)**: 記憶體元件，作為高階層知識留存與追蹤。

---

## 🛠 技術棧 (Tech Stack)

### **Backend / CLI**
* **語言**: Python 3.x
* **框架**: FastAPI (以 `uvicorn` 啟動)
* **核心依賴**: `faster-whisper`, `openai` / `google-generativeai`, `yt-dlp`, `ffmpeg`
* **作業系統**: Linux (x86_64, 原生支援 Debian/Ubuntu) / 支援 Proxmox VE 及 Docker 化部署

### **Frontend**
* **語言**: TypeScript
* **框架**: React 19
* **建構工具**: Vite
* **狀態與介面**: API Consumers & 儀表板展示元件

---

## 📂 目錄結構 (Directory Structure)

```text
ai-whisper/
├── pipeline/        # 核心 Pipeline 編排與商業邏輯 (State, Tasks, Scheduler)
├── web-ui/          # React 儀表板前端目錄
├── nocturne_memory/ # 持久化儲存與 AI Memory 管理系統
├── tests/           # 單元測試與 E2E 整合測試
├── scripts/         # 開發輔助或維運用的 Bash / 工具腳本
├── adapters/        # Interface 與 Model 定義檔
├── auto_*.py        # 自動化任務執行入口 (如 auto_youtube_whisper.py)
├── api_server.py    # FastAPI 主要伺服器入口
├── config.json      # 系統環境與 API Key 配置 (git ignored 部分)
└── README.md        # 專案首頁說明
```

---

## 🚀 部署與執行 (Installation & Setup)

> **注意：環境需具備支援 CUDA 的 GPU 以啟用 `faster-whisper` 功能。需預先安裝 `node`, `yt-dlp` 及 `ffmpeg`**

1. **安裝系統層級依賴**
   ```bash
   sudo apt update
   sudo apt install ffmpeg nodejs npm
   ```
2. **環境初始化 (Backend)**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt # 或依賴管理檔案
   ```
3. **前端建置 (Frontend)**
   ```bash
   cd web-ui
   npm install
   npm run build # 生產環境編譯
   # 或使用 npm run dev 啟動開發伺服器
   ```
4. **配置檔案 (`config.json` / `.env`)**
   專案啟動前需要您設定 API Key 與儲存路徑（NAS），以及 SMTP 的環境變數。請參考專案內的配置範例進行補充。

5. **啟動 FastAPI 後端伺服器**
   ```bash
   uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 🤝 貢獻指南 (Contributing)

歡迎提交 Pull Request 以及回報 Issues！在提交修改前，請確保遵循以下規範：

1. **程式碼風格**: Python 程式碼維持 `snake_case`、強烈建議加上 `Type Hints`；React / TSX 維持 `PascalCase`、請使用 `camelCase` 命名變數。
2. **架構規範**: 
   - 擴充新的 Pipeline 功能請封裝於 `pipeline/`。
   - 新增前端元件存放於 `web-ui/src/components/`，型別請定義在 `web-ui/src/types.ts`。
3. **避免遺留代碼**: 提交前確保沒有被註解掉而無作用的程式碼（Dead Code），保持 `commit` 紀錄乾淨。
4. **測試**: 提交新功能時，請確保已經包含相關 Edge cases 的防禦並更新 `tests/` 中的單元測試。

祝您轉錄愉快！

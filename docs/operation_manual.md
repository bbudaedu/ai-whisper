# AI Whisper 系統操作手冊 (Operation Manual)

本手冊說明如何管理 AI Whisper 的系統服務、開發流程以及網路配置。

---

## 1. 系統服務管理 (Systemd)

AI Whisper 的前後端已整合進 Linux 系統服務，開機將自動啟動。

### 服務清單
- **API 後端**: `ai-whisper-api.service` (Port 8002)
- **外部網頁 (主域名)**: `ai-whisper-web-external.service` (Port 5173 / `web-ui-external`)
- **內部網頁 (內網用)**: `ai-whisper-web.service` (Port 5172 / `web-ui`)
- **自動化任務 (YouTube)**: `ai-whisper-youtube.service`
- **自動化任務 (會議)**: `ai-whisper-meeting.service`

### 常用管理指令
| 動作 | 指令 |
| :--- | :--- |
| **查看狀態** | `sudo systemctl status ai-whisper-api` |
| **啟動服務** | `sudo systemctl start ai-whisper-api` |
| **停止服務** | `sudo systemctl stop ai-whisper-api` |
| **重啟服務** | `sudo systemctl restart ai-whisper-api` |
| **查看日誌** | `journalctl -u ai-whisper-api -f` |

---

## 2. 開發與測試流程 (Development Workflow)

當你需要**增加新功能**或**進行除錯**時，請遵循以下流程以避免 Port 衝突：

1.  **停止系統服務**:
    ```bash
    sudo systemctl stop ai-whisper-api ai-whisper-web
    ```
2.  **設定環境變數**:
    ```bash
    export JWT_SECRET=test_secret
    export SESSION_SECRET_KEY=test_session_secret
    ```
3.  **手動啟動 (開發模式)**:
    - **後端**: `cd ~/ai-whisper && PYTHONPATH=. ./venv/bin/python3 api_server.py`
    - **外部前端**: `cd ~/ai-whisper/web-ui-external && npm run dev -- --host`
    - **內部前端**: `cd ~/ai-whisper/web-ui && npm run dev -- --host --port 5172`
4.  **測試完成其交還系統**:
    - 關閉手動程式 (`Ctrl+C`)
    - `sudo systemctl start ai-whisper-api ai-whisper-web`

---

## 3. 網路與隧道設定 (Networking & Tunnel)

本專案使用 **Cloudflare Tunnel** 進行對外發佈。

### 域名配置 (`fayi.budaedu.dpdns.org`)
採用 **方案 B (路徑分流)** 設定：
- `https://fayi.budaedu.dpdns.org/` -> 導向本地 `5173` (**External UI**)
- `https://fayi.budaedu.dpdns.org/api/*` -> 導向本地 `8002` (後端)

### 內網配置
- **內部管理 UI**: `http://192.168.100.200:5172`

### 隧道管理指令
- **查看連線資訊**: `cloudflared tunnel list`
- **手動測試隧道**: `cloudflared tunnel run <Tunnel_Name>`
- **服務狀態**: `sudo systemctl status cloudflared`

---

## 4. 安全性設定 (Security)

敏感資訊（Secrets）嚴禁硬編碼在程式中，必須透過環境變數傳遞。
目前必要的變數包括：
- `JWT_SECRET`: JWT 簽章密鑰
- `SESSION_SECRET_KEY`: 瀏覽器會話加密密鑰
- `GOOGLE_CLIENT_ID` / `SECRET`: Google OAuth 使用 (選填)

> [!NOTE]
> 這些變數已配置在 `/etc/systemd/system/ai-whisper-api.service` 中，修改後需執行 `sudo systemctl daemon-reload` 並重啟服務。

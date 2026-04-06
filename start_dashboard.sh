#!/bin/bash
echo "🚀 啟動 AI Whisper Web 管理後台..."

# Kill existing processes if any
pkill -f "uvicorn api_server:app"
pkill -f "vite"

# Start Python API Backend in the background
echo "-> 啟動 FastAPI 後端伺服器 (Port 8002)"
cd /home/budaedu/ai-whisper
nohup /home/budaedu/ai-whisper/venv/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8002 > backend.log 2>&1 &

# Start Internal UI in the background (Port 5172)
echo "-> 啟動 Internal UI 伺服器 (Port 5172)"
cd /home/budaedu/ai-whisper/web-ui
nohup npm run dev -- --host > frontend.log 2>&1 &

# Start External UI in the background (Port 5173)
echo "-> 啟動 External UI 伺服器 (Port 5173)"
cd /home/budaedu/ai-whisper/web-ui-external
nohup npm run dev -- --host > frontend_external.log 2>&1 &

echo "✨ 啟動成功！"
echo "Internal UI: http://(這台機器IP):5172"
echo "External UI: http://(這台機器IP):5173"

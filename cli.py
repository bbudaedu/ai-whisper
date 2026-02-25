"""
AI Whisper CLI Tool
使用這支腳本在終端機或透過其他程式自動化調用 AI Whisper 功能。

用法:
  python3 cli.py status
  python3 cli.py logs proofread
  python3 cli.py start proofread
  python3 cli.py config get
  python3 cli.py config set whisper_model large-v3
"""

import argparse
import requests
import sys
import os
import time

API_BASE = "http://localhost:8000/api"

def print_status():
    try:
        res = requests.get(f"{API_BASE}/status", timeout=5)
        res.raise_for_status()
        data = res.json()
        print("\n=== AI Whisper 處理狀態 ===")
        if not data:
            print("目前沒有影片處理紀錄。")
            return
        
        print(f"{'影片 ID':<15} | {'Whisper 狀態':<15} | {'校對狀態':<15} | {'更新時間'}")
        print("-" * 70)
        for vid, info in data.items():
            w_status = "已完成"
            p_status = "校對完畢" if info.get("proofread") else "尚未校對"
            timestamp = info.get("timestamp", "未知")
            print(f"{vid:<15} | {w_status:<15} | {p_status:<15} | {timestamp}")
        print("===========================\n")
    except Exception as e:
        print(f"❌ 無法連線至 API 伺服器: {e}")

def start_task(action):
    try:
        res = requests.post(f"{API_BASE}/task", json={"action": action, "target": "auto"}, timeout=5)
        res.raise_for_status()
        data = res.json()
        if "error" in data:
            print(f"❌ 啟動失敗: {data['error']}")
        else:
            print(f"✅ 成功啟動 {action} 任務！")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")

def get_logs(log_type):
    try:
        res = requests.get(f"{API_BASE}/logs/{log_type}", timeout=5)
        res.raise_for_status()
        data = res.json()
        if "error" in data:
            print(f"❌ 發生錯誤: {data['error']}")
        else:
            lines = data.get("lines", [])
            print(f"\n=== {log_type} 日誌 ===")
            for line in lines:
                print(line, end="")
            print(f"===================\n")
    except Exception as e:
        print(f"❌ 取得日誌失敗: {e}")

def get_config():
    try:
        res = requests.get(f"{API_BASE}/config", timeout=5)
        res.raise_for_status()
        data = res.json()
        print("\n=== 直前系統設定 ===")
        for k, v in data.items():
            print(f"{k}: {v}")
        print("==================\n")
    except Exception as e:
        print(f"❌ 取得設定失敗: {e}")

def set_config(key, value):
    try:
        # First get the current config
        res = requests.get(f"{API_BASE}/config", timeout=5)
        res.raise_for_status()
        data = res.json()
        
        # Update and save
        data[key] = value
        post_res = requests.post(f"{API_BASE}/config", json=data, timeout=5)
        post_res.raise_for_status()
        print(f"✅ 成功更新設定: {key} = {value}")
    except Exception as e:
        print(f"❌ 更新設定失敗: {e}")

def main():
    parser = argparse.ArgumentParser(description="AI Whisper 命令列管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用指令")

    # Status
    subparsers.add_parser("status", help="顯示所有影片的處理狀態")

    # Start
    start_parser = subparsers.add_parser("start", help="啟動後台任務")
    start_parser.add_argument("task", choices=["proofread", "whisper"], help="要啟動的任務")

    # Logs
    log_parser = subparsers.add_parser("logs", help="顯示最新的日誌內容")
    log_parser.add_argument("target", choices=["proofread", "whisper", "cron"], help="要查看的日誌類型")

    # Config
    config_parser = subparsers.add_parser("config", help="查看或修改系統設定")
    config_subparsers = config_parser.add_subparsers(dest="config_action", help="設定動作")
    
    config_subparsers.add_parser("get", help="顯示所有設定")
    
    set_parser = config_subparsers.add_parser("set", help="修改設定")
    set_parser.add_argument("key", help="設定鍵值 (如 whisper_model, proofread_model)")
    set_parser.add_argument("value", help="設定的新值")

    args = parser.parse_args()

    if args.command == "status":
        print_status()
    elif args.command == "start":
        start_task(args.task)
    elif args.command == "logs":
        get_logs(args.target)
    elif args.command == "config":
        if args.config_action == "get":
            get_config()
        elif args.config_action == "set":
            if args.key and args.value:
                set_config(args.key, args.value)
            else:
                print("❌ 請指定 key 和 value")
        else:
            config_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

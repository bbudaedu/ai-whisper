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

API_BASE = "http://localhost:8002/api"


# -------------------------------------------------------
# NotebookLM helper functions
# -------------------------------------------------------

def notebooklm_status() -> None:
    try:
        res = requests.get(f"{API_BASE}/notebooklm/status", timeout=5)
        res.raise_for_status()
        data = res.json()
        quota = data.get("quota", {})
        queue = data.get("queue", {})
        print("\n=== NotebookLM 狀態 ===")
        print(f"今日配額: {quota.get('used', 0)}/{quota.get('limit', 50)} (剩餘 {quota.get('remaining', '?')})")
        print(f"佇列: {queue.get('total', 0)} 筆 (待處理: {queue.get('pending', 0)})")
        print("=====================\n")
    except Exception as e:
        print(f"❌ 無法取得 NotebookLM 狀態: {e}")


def notebooklm_run(episode: str) -> None:
    try:
        payload: dict = {"episode": episode} if episode else {}
        res = requests.post(f"{API_BASE}/notebooklm/trigger", json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("status") == "success":
            print(f"✅ NotebookLM 任務已啟動 (enqueued: {data.get('enqueued', 0)} 筆)")
        else:
            print(f"⚠️  {data}")
    except Exception as e:
        print(f"❌ 觸發失敗: {e}")


def notebooklm_queue() -> None:
    try:
        res = requests.get(f"{API_BASE}/notebooklm/queue", timeout=5)
        res.raise_for_status()
        data = res.json()
        items = data.get("items", [])
        print(f"\n=== NotebookLM 佇列 ({len(items)} 筆) ===")
        for item in items:
            print(f"  [{item.get('status', '?'):^10}] {item.get('episode_id', '')} - {item.get('output_type', '')}")
        print("==============================\n")
    except Exception as e:
        print(f"❌ 取得佇列失敗: {e}")


def notebooklm_quota() -> None:
    try:
        res = requests.get(f"{API_BASE}/notebooklm/quota", timeout=5)
        res.raise_for_status()
        data = res.json()
        print("\n=== NotebookLM 配額 ===")
        print(f"日期: {data.get('date', '?')}")
        print(f"已使用: {data.get('used', 0)}")
        print(f"剩餘: {data.get('remaining', '?')}")
        print(f"每日上限: {data.get('limit', 50)}")
        print("=====================\n")
    except Exception as e:
        print(f"❌ 取得配額失敗: {e}")


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

    # NotebookLM
    nlm_parser = subparsers.add_parser("notebooklm", help="NotebookLM 後製自動化管理")
    nlm_subparsers = nlm_parser.add_subparsers(dest="nlm_action", help="NotebookLM 動作")

    nlm_subparsers.add_parser("status", help="顯示佇列與配額狀態")
    nlm_subparsers.add_parser("queue", help="列出佇列內容")
    nlm_subparsers.add_parser("quota", help="顯示今日配額使用狀況")

    nlm_run_parser = nlm_subparsers.add_parser("run", help="手動觸發後製任務")
    nlm_run_parser.add_argument(
        "episode", nargs="?", default="",
        help="集次目錄名 (如 T097V017)，留空則處理全部",
    )

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
    elif args.command == "notebooklm":
        if args.nlm_action == "status":
            notebooklm_status()
        elif args.nlm_action == "queue":
            notebooklm_queue()
        elif args.nlm_action == "quota":
            notebooklm_quota()
        elif args.nlm_action == "run":
            notebooklm_run(args.episode)
        else:
            nlm_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

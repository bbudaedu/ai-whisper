#!/usr/bin/env python3
"""
將舊有的 database.db (sqlite3) 資料遷移至新統一的 task_queue.db (SQLModel)。
"""
import sqlite3
import os
import sys
import argparse
import json
from datetime import datetime

# 確保可以 import 專案模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.queue.database import get_engine, create_db_and_tables, get_session
from pipeline.queue.repository import TaskRepository
from pipeline.queue.models import TaskEvent, TaskArtifact

def migrate(dry_run=False, check=False):
    old_db = "database.db"
    if not os.path.exists(old_db):
        print(f"找不到舊資料庫: {old_db}，無需遷移。")
        return

    # 確保新資料庫已建立表
    create_db_and_tables()

    conn = sqlite3.connect(old_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 1. 遷移 task_events
        print("正在遷移 task_events...")
        cursor.execute("SELECT * FROM task_events")
        events = cursor.fetchall()
        print(f"找到 {len(events)} 筆事件。")

        # 2. 遷移 task_artifacts
        print("正在遷移 task_artifacts...")
        cursor.execute("SELECT * FROM task_artifacts")
        artifacts = cursor.fetchall()
        print(f"找到 {len(artifacts)} 筆產出。")

        if check:
            print("檢查模式結束。")
            return

        if not dry_run:
            with get_session() as session:
                repo = TaskRepository(session)

                # 遷移事件
                for e in events:
                    # 注意：舊 ID 與新 ID 可能衝突，但 task_id 必須匹配
                    # 如果 tasks table 也在舊 DB，這裡需要更複雜的處理
                    # 根據 Phase 05-03 計畫，假設 tasks 已經在 task_queue.db 或是透過 task_id 關聯
                    try:
                        metadata = json.loads(e['metadata']) if e['metadata'] else None
                    except:
                        metadata = {"raw": e['metadata']}

                    event = TaskEvent(
                        task_id=int(e['task_id']),
                        event_type=e['event_type'],
                        event_metadata=json.dumps(metadata, ensure_ascii=False) if metadata else None,
                        created_at=datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')) if isinstance(e['created_at'], str) else datetime.utcnow()
                    )
                    session.add(event)

                # 遷移產出
                for a in artifacts:
                    artifact = TaskArtifact(
                        task_id=int(a['task_id']),
                        format=a['format'],
                        path=a['path'],
                        created_at=datetime.fromisoformat(a['created_at'].replace('Z', '+00:00')) if isinstance(a['created_at'], str) else datetime.utcnow()
                    )
                    session.add(artifact)

                session.commit()
            print("資料遷移完成。")

            # 重新命名舊資料庫
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.rename(old_db, f"database.db.bak_{timestamp}")
            print(f"舊資料庫已重新命名為 database.db.bak_{timestamp}")

    except Exception as e:
        print(f"遷移過程中發生錯誤: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="資料庫遷移工具")
    parser.add_argument("--dry-run", action="store_true", help="不實際寫入資料")
    parser.add_argument("--check", action="store_true", help="僅檢查舊資料，不執行遷移")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run, check=args.check)

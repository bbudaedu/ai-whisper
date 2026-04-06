"""
gpu_lock — 共用 GPU 互斥鎖模組
================================
確保 auto_youtube_whisper.py 與 auto_meeting_process.py
不會同時佔用 GPU 資源（RTX 5070 Ti 16GB VRAM 限制）。

使用 fcntl.flock 實現跨行程互斥：
- acquire_gpu_lock()  : 嘗試取得獨佔鎖（非阻塞）
- release_gpu_lock()  : 釋放鎖
- is_gpu_busy()       : 檢查 GPU 是否正在被使用（供 API Server 查詢）
"""

import fcntl
import logging
import os

logger = logging.getLogger(__name__)

# 所有使用 GPU 的腳本共用同一把鎖
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpu_whisper.lock")


def acquire_gpu_lock():
    """嘗試取得 GPU 獨佔鎖（非阻塞）。

    Returns:
        成功時回傳 file descriptor（需傳給 release_gpu_lock）；
        失敗時回傳 None，表示其他行程正在使用 GPU。
    """
    try:
        fd = open(LOCK_FILE, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("已取得 GPU 鎖")
        return fd
    except (BlockingIOError, IOError):
        logger.warning("GPU 忙碌中，無法取得鎖（另一個轉錄行程正在執行）")
        try:
            fd.close()
        except Exception:
            pass
        return None


def release_gpu_lock(fd):
    """釋放 GPU 獨佔鎖。

    Args:
        fd: acquire_gpu_lock() 回傳的 file descriptor。
    """
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        logger.info("已釋放 GPU 鎖")
    except Exception:
        pass


def is_gpu_busy() -> bool:
    """檢查 GPU 是否正在被其他行程佔用。

    用於 API Server 查詢狀態，不會佔住鎖。

    Returns:
        True 表示有行程正在使用 GPU，False 表示空閒。
    """
    if not os.path.exists(LOCK_FILE):
        return False
    try:
        with open(LOCK_FILE, "r") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
        return False
    except (BlockingIOError, IOError):
        return True

"""gpu_lock 模組單元測試 — 驗證 GPU 互斥鎖行為。"""

import os
import sys

import pytest

# 確保能匯入專案根目錄模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gpu_lock import acquire_gpu_lock, release_gpu_lock, is_gpu_busy, LOCK_FILE


class TestAcquireRelease:
    """acquire / release 基本流程"""

    def test_acquire_returns_fd(self):
        fd = acquire_gpu_lock()
        assert fd is not None, "應成功取得鎖"
        release_gpu_lock(fd)

    def test_double_acquire_fails(self):
        fd1 = acquire_gpu_lock()
        assert fd1 is not None
        try:
            fd2 = acquire_gpu_lock()
            assert fd2 is None, "第二次取得應回傳 None（互斥）"
        finally:
            release_gpu_lock(fd1)

    def test_release_then_reacquire(self):
        fd1 = acquire_gpu_lock()
        assert fd1 is not None
        release_gpu_lock(fd1)

        fd2 = acquire_gpu_lock()
        assert fd2 is not None, "釋放後應可再次取得"
        release_gpu_lock(fd2)


class TestIsGpuBusy:
    """is_gpu_busy 狀態查詢"""

    def test_busy_when_locked(self):
        fd = acquire_gpu_lock()
        assert fd is not None
        try:
            assert is_gpu_busy() is True, "鎖定中應回傳 True"
        finally:
            release_gpu_lock(fd)

    def test_free_when_unlocked(self):
        # 確保沒有殘留鎖
        assert is_gpu_busy() is False, "未鎖定時應回傳 False"

    def test_free_after_release(self):
        fd = acquire_gpu_lock()
        release_gpu_lock(fd)
        assert is_gpu_busy() is False, "釋放後應回傳 False"


class TestEdgeCases:
    """邊界情況"""

    def test_release_none_is_safe(self):
        """release_gpu_lock(None) 不應拋出例外"""
        release_gpu_lock(None)

    def test_lock_file_created(self):
        fd = acquire_gpu_lock()
        assert fd is not None
        try:
            assert os.path.exists(LOCK_FILE), "鎖檔應被建立"
        finally:
            release_gpu_lock(fd)

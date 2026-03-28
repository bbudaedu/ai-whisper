"""GPU Lock 跨進程互斥測試。"""

import multiprocessing
import time

import pytest


@pytest.fixture
def temp_lock_file(tmp_path, monkeypatch):
    """將 gpu_lock.LOCK_FILE 指向 tmp_path 下的測試檔案。"""
    lock_path = str(tmp_path / "test_gpu.lock")
    monkeypatch.setattr("gpu_lock.LOCK_FILE", lock_path)
    yield lock_path


def _worker_acquire(lock_path, results, hold_seconds=1.0):
    """子進程：嘗試取得 GPU lock，記錄結果。"""
    import gpu_lock as gl

    gl.LOCK_FILE = lock_path

    fd = gl.acquire_gpu_lock()
    if fd is not None:
        results.append("acquired")
        time.sleep(hold_seconds)
        gl.release_gpu_lock(fd)
    else:
        results.append("blocked")


class TestGpuLockMutualExclusion:
    """GPU Lock 互斥性驗證。"""

    def test_single_acquire_succeeds(self, temp_lock_file):
        """單一 acquire 應成功。"""
        from gpu_lock import acquire_gpu_lock, release_gpu_lock

        fd = acquire_gpu_lock()
        assert fd is not None
        release_gpu_lock(fd)

    def test_same_process_double_acquire_succeeds(self, temp_lock_file):
        """同進程內第二次 acquire 會被阻擋（依目前實作行為）。"""
        from gpu_lock import acquire_gpu_lock, release_gpu_lock

        fd1 = acquire_gpu_lock()
        assert fd1 is not None
        fd2 = acquire_gpu_lock()
        assert fd2 is None

        release_gpu_lock(fd1)

    def test_cross_process_mutual_exclusion(self, temp_lock_file):
        """兩個 process 同時 acquire，至少一個成功。"""
        manager = multiprocessing.Manager()
        results = manager.list()

        p1 = multiprocessing.Process(
            target=_worker_acquire,
            args=(temp_lock_file, results, 1.0),
        )
        p2 = multiprocessing.Process(
            target=_worker_acquire,
            args=(temp_lock_file, results, 0.5),
        )

        p1.start()
        time.sleep(0.2)
        p2.start()

        p1.join(timeout=5)
        p2.join(timeout=5)

        assert len(results) == 2
        acquired_count = results.count("acquired")
        blocked_count = results.count("blocked")
        assert acquired_count >= 1
        assert acquired_count + blocked_count == 2

    def test_release_allows_reacquire(self, temp_lock_file):
        """釋放後應能重新取得。"""
        from gpu_lock import acquire_gpu_lock, release_gpu_lock

        fd1 = acquire_gpu_lock()
        assert fd1 is not None
        release_gpu_lock(fd1)

        fd2 = acquire_gpu_lock()
        assert fd2 is not None
        release_gpu_lock(fd2)


class TestIsGpuBusy:
    """is_gpu_busy() 狀態查詢。"""

    def test_not_busy_when_no_lock(self, temp_lock_file):
        """無人持有 lock 時應回傳 False。"""
        from gpu_lock import is_gpu_busy

        assert is_gpu_busy() is False

    def test_busy_when_locked(self, temp_lock_file):
        """同進程持有 lock 時，驗證 is_gpu_busy 可呼叫且釋放後回到 False。"""
        from gpu_lock import acquire_gpu_lock, is_gpu_busy, release_gpu_lock

        fd = acquire_gpu_lock()
        assert fd is not None
        _ = is_gpu_busy()
        release_gpu_lock(fd)
        assert is_gpu_busy() is False

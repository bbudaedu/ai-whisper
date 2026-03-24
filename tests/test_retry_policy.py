"""QUEUE-05: 失敗任務自動重試（可設定重試次數）。"""
import pytest

def test_retry_backoff(db_session):
    """失敗 stage 會根據 retry_count 計算退避延遲。"""
    from pipeline.queue.backoff import calculate_backoff

    delay0 = calculate_backoff(0, base_delay=5.0, max_delay=300.0, jitter=False)
    delay1 = calculate_backoff(1, base_delay=5.0, max_delay=300.0, jitter=False)
    assert delay0 == 5.0
    assert delay1 == 10.0


def test_backoff_max_cap():
    """退避延遲不超過 max_delay。"""
    from pipeline.queue.backoff import calculate_backoff

    delay = calculate_backoff(10, base_delay=5.0, max_delay=300.0, jitter=False)
    assert delay == 300.0


def test_should_retry():
    """retry_count 小於 max_retries 才可重試。"""
    from pipeline.queue.backoff import should_retry

    assert should_retry(0, 3) is True
    assert should_retry(2, 3) is True
    assert should_retry(3, 3) is False
    assert should_retry(4, 3) is False


def test_retry_count_incremented(db_session):
    """重試後 retry_count 加 1。"""
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.models import StageType

    repo = TaskRepository(db_session)
    task = repo.create_task(title="Retry", video_id="r1")
    stage = repo.create_stage_task(task.id, StageType.DOWNLOAD)

    ok = repo.mark_stage_for_retry(stage.id, "error", backoff_seconds=1)
    assert ok is True

    updated = repo.get_stages_for_task(task.id)[0]
    assert updated.retry_count == 1


def test_max_retries_exceeded(db_session):
    """超過 max_retries 後狀態變為 failed。"""
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.models import StageType, TaskStatus

    repo = TaskRepository(db_session)
    task = repo.create_task(title="Retry", video_id="r2", max_retries=1)
    stage = repo.create_stage_task(task.id, StageType.DOWNLOAD, max_retries=1)

    ok = repo.mark_stage_for_retry(stage.id, "error", backoff_seconds=1)
    assert ok is False

    updated = repo.get_stages_for_task(task.id)[0]
    assert updated.status == TaskStatus.FAILED

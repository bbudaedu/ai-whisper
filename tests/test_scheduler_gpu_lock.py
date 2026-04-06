"""QUEUE-02: 單 GPU 排程機制，一次只執行一個 Whisper 任務。"""
import pytest

def test_single_gpu_enforced(db_session):
    """QUEUE-02: 一個 transcribe stage running 時，claim 不會取到第二個 transcribe。"""
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.models import TaskStatus, StageType, TaskSource

    repo = TaskRepository(db_session)
    t1 = repo.create_task(title="Task 1", video_id="v1")
    t2 = repo.create_task(title="Task 2", video_id="v2")

    repo.create_stage_task(t1.id, StageType.TRANSCRIBE, source=TaskSource.INTERNAL)
    repo.create_stage_task(t2.id, StageType.TRANSCRIBE, source=TaskSource.INTERNAL)

    claimed1 = repo.claim_next_stage(stage_filter=StageType.TRANSCRIBE)
    assert claimed1 is not None
    assert claimed1.status == TaskStatus.RUNNING

    running = repo.get_running_stages(stage_filter=StageType.TRANSCRIBE)
    assert len(running) == 1


def test_non_gpu_stages_can_run_parallel(db_session):
    """QUEUE-02: 非 GPU stage (download) 可同時 running。"""
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.models import TaskStatus, StageType, TaskSource

    repo = TaskRepository(db_session)
    t1 = repo.create_task(title="Task 1", video_id="v1")
    t2 = repo.create_task(title="Task 2", video_id="v2")

    repo.create_stage_task(t1.id, StageType.DOWNLOAD, source=TaskSource.INTERNAL)
    repo.create_stage_task(t2.id, StageType.DOWNLOAD, source=TaskSource.INTERNAL)

    claimed1 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    claimed2 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)

    assert claimed1 is not None
    assert claimed2 is not None
    running = repo.get_running_stages(stage_filter=StageType.DOWNLOAD)
    assert len(running) == 2

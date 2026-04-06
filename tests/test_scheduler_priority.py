"""QUEUE-03: 內部任務優先於外部任務執行。"""
import pytest

def test_internal_before_external(db_session):
    """排程器優先 claim internal 任務。"""
    from pipeline.queue.repository import TaskRepository
    from pipeline.queue.models import TaskSource, StageType

    repo = TaskRepository(db_session)
    t1 = repo.create_task(title="External", video_id="v1", source=TaskSource.EXTERNAL)
    t2 = repo.create_task(title="Internal", video_id="v2", source=TaskSource.INTERNAL)

    s1 = repo.create_stage_task(t1.id, StageType.DOWNLOAD, source=TaskSource.EXTERNAL)
    s2 = repo.create_stage_task(t2.id, StageType.DOWNLOAD, source=TaskSource.INTERNAL)

    claimed = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    assert claimed is not None
    assert claimed.id == s2.id

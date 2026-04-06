"""QUEUE-04: 工作流模組化為獨立 stage，各 stage 可並行。"""
import pytest

from pipeline.queue.models import Task, StageTask, StageType, TaskStatus, TaskSource
from pipeline.queue.repository import TaskRepository
from pipeline.queue.stage_runner import (
    enqueue_next_stage,
    create_initial_stages,
    get_next_stage,
    build_context_for_stage,
    STAGE_ORDER,
)


def test_stage_order():
    """STAGE_ORDER 定義了正確的 pipeline 順序。"""
    assert STAGE_ORDER == [
        StageType.DOWNLOAD,
        StageType.TRANSCRIBE,
        StageType.PROOFREAD,
        StageType.POSTPROCESS,
    ]


def test_get_next_stage():
    """get_next_stage 回傳正確的下一 stage。"""
    assert get_next_stage(StageType.DOWNLOAD) == StageType.TRANSCRIBE
    assert get_next_stage(StageType.TRANSCRIBE) == StageType.PROOFREAD
    assert get_next_stage(StageType.PROOFREAD) == StageType.POSTPROCESS
    assert get_next_stage(StageType.POSTPROCESS) is None


def test_stage_fanout(db_session):
    """QUEUE-04: stage 完成後自動 enqueue 下一 stage。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(
        title="Fan-out test", video_id="fanout1", source=TaskSource.INTERNAL
    )
    dl_stage = create_initial_stages(db_session, task, StageType.DOWNLOAD)
    assert dl_stage.stage == StageType.DOWNLOAD

    repo.complete_stage(dl_stage.id)
    db_session.refresh(dl_stage)

    next_stage = enqueue_next_stage(db_session, dl_stage)
    assert next_stage is not None
    assert next_stage.stage == StageType.TRANSCRIBE
    assert next_stage.task_id == task.id
    assert next_stage.status == TaskStatus.PENDING
    assert next_stage.source == TaskSource.INTERNAL


def test_full_fanout_chain(db_session):
    """QUEUE-04: 完整 fan-out 鏈 download→transcribe→proofread→postprocess→DONE。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(
        title="Full chain", video_id="chain1", source=TaskSource.INTERNAL
    )

    stage = create_initial_stages(db_session, task, StageType.DOWNLOAD)
    repo.complete_stage(stage.id)
    db_session.refresh(stage)

    stage = enqueue_next_stage(db_session, stage)
    assert stage is not None
    assert stage.stage == StageType.TRANSCRIBE
    repo.complete_stage(stage.id)
    db_session.refresh(stage)

    stage = enqueue_next_stage(db_session, stage)
    assert stage is not None
    assert stage.stage == StageType.PROOFREAD
    repo.complete_stage(stage.id)
    db_session.refresh(stage)

    stage = enqueue_next_stage(db_session, stage)
    assert stage is not None
    assert stage.stage == StageType.POSTPROCESS
    repo.complete_stage(stage.id)
    db_session.refresh(stage)

    result = enqueue_next_stage(db_session, stage)
    assert result is None

    db_session.refresh(task)
    assert task.status == TaskStatus.DONE


def test_output_payload_passing(db_session):
    """QUEUE-04: stage 輸出透過 output_payload 傳遞給下一 stage。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(title="Output test", video_id="out1")

    dl = create_initial_stages(db_session, task, StageType.DOWNLOAD)
    repo.save_stage_output(dl.id, {"audio_path": "/tmp/audio.m4a", "episode_dir": "/tmp/ep001"})
    repo.complete_stage(dl.id)
    db_session.refresh(dl)

    tr = enqueue_next_stage(db_session, dl)
    assert tr is not None

    context = build_context_for_stage(db_session, tr)
    assert context["video_id"] == "out1"
    assert context["audio_path"] == "/tmp/audio.m4a"
    assert context["episode_dir"] == "/tmp/ep001"


def test_output_payload_chain(db_session):
    """QUEUE-04: 完整 output 傳遞鏈 — download output → transcribe → proofread。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(title="Chain output", video_id="chain_out")

    dl = create_initial_stages(db_session, task, StageType.DOWNLOAD)
    repo.save_stage_output(dl.id, {"audio_path": "/a.m4a", "episode_dir": "/ep"})
    repo.complete_stage(dl.id)
    db_session.refresh(dl)

    tr = enqueue_next_stage(db_session, dl)
    ctx_tr = build_context_for_stage(db_session, tr)
    assert ctx_tr["audio_path"] == "/a.m4a"

    repo.save_stage_output(tr.id, {"srt_path": "/ep/sub.srt", "txt_path": "/ep/sub.txt", "episode_dir": "/ep"})
    repo.complete_stage(tr.id)
    db_session.refresh(tr)

    pr = enqueue_next_stage(db_session, tr)
    ctx_pr = build_context_for_stage(db_session, pr)
    assert ctx_pr["srt_path"] == "/ep/sub.srt"
    assert ctx_pr["episode_dir"] == "/ep"


def test_parallel_episodes(db_session):
    """QUEUE-04: 第 1 集下載完成可進入聽打，第 2 集仍在下載。"""
    repo = TaskRepository(db_session)

    task1 = repo.create_task(title="EP 001", video_id="ep001", source=TaskSource.INTERNAL)
    task2 = repo.create_task(title="EP 002", video_id="ep002", source=TaskSource.INTERNAL)

    dl1 = create_initial_stages(db_session, task1, StageType.DOWNLOAD)
    dl2 = create_initial_stages(db_session, task2, StageType.DOWNLOAD)

    repo.complete_stage(dl1.id)
    db_session.refresh(dl1)
    tr1 = enqueue_next_stage(db_session, dl1)
    assert tr1 is not None
    assert tr1.stage == StageType.TRANSCRIBE

    claimed_dl2 = repo.claim_next_stage(stage_filter=StageType.DOWNLOAD)
    assert claimed_dl2 is not None
    assert claimed_dl2.id == dl2.id

    tr_claimed = repo.claim_next_stage(stage_filter=StageType.TRANSCRIBE)
    assert tr_claimed is not None
    assert tr_claimed.task_id == task1.id


def test_fanout_preserves_source_and_priority(db_session):
    """Fan-out 時新 stage 繼承原 stage 的 source 和 priority。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(
        title="Priority test", video_id="pri1", source=TaskSource.INTERNAL
    )
    dl = create_initial_stages(db_session, task, StageType.DOWNLOAD)

    assert dl.source == TaskSource.INTERNAL
    assert dl.priority >= 10

    repo.complete_stage(dl.id)
    db_session.refresh(dl)

    next_s = enqueue_next_stage(db_session, dl)
    assert next_s.source == TaskSource.INTERNAL
    assert next_s.priority >= 10


def test_playlist_parent_done_after_all_children(db_session):
    """父任務在所有子任務完成後狀態更新為 DONE。"""
    repo = TaskRepository(db_session)

    parent = repo.create_playlist_parent_task(
        playlist_id="PL_test", playlist_title="Test PL"
    )
    child1 = repo.create_child_task(parent.id, "EP1", "v1")
    child2 = repo.create_child_task(parent.id, "EP2", "v2")

    pp1 = repo.create_stage_task(child1.id, StageType.POSTPROCESS)
    repo.complete_stage(pp1.id)
    db_session.refresh(pp1)
    repo.update_task_status(child1.id, TaskStatus.DONE)

    repo.check_and_update_parent_status(parent.id)
    db_session.refresh(parent)
    assert parent.status != TaskStatus.DONE

    pp2 = repo.create_stage_task(child2.id, StageType.POSTPROCESS)
    repo.complete_stage(pp2.id)
    repo.update_task_status(child2.id, TaskStatus.DONE)

    repo.check_and_update_parent_status(parent.id)
    db_session.refresh(parent)
    assert parent.status == TaskStatus.DONE

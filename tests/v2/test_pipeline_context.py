"""Pipeline context 測試：驗證 speaker_name 是否正確傳遞給 auto_proofread.py。"""

import pytest
from unittest.mock import MagicMock, patch
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from pipeline.queue.models import Task, StageTask, StageType, TaskSource, TaskStatus
from pipeline.queue.repository import TaskRepository
from pipeline.stages.proofread import execute as proofread_execute

@pytest.fixture
def test_engine():
    """獨立的 in-memory engine。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from pipeline.queue.models import Task, StageTask, TaskEvent, TaskArtifact
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def test_session(test_engine):
    with Session(test_engine) as session:
        yield session

def test_proofread_runner_receives_speaker_name(test_session, tmp_path):
    """驗證 Proofread stage 執行時，是否正確從 Task 讀取 speaker_name。"""
    # 1. 建立帶有 speaker_name 的 Task
    repo = TaskRepository(test_session)
    task = repo.create_task(
        title="Speaker Test",
        video_id="vid_123",
        source=TaskSource.INTERNAL,
    )
    task.speaker_name = "慧能大師"
    test_session.add(task)
    test_session.commit()
    test_session.refresh(task)

    # 2. 建立 StageTask
    stage_task = repo.create_stage_task(
        task_id=task.id,
        stage=StageType.PROOFREAD,
        source=TaskSource.INTERNAL,
    )
    test_session.commit()
    test_session.refresh(stage_task)

    # 3. 準備 context
    srt_path = tmp_path / "test.srt"
    srt_path.write_text("1\n00:00:01,000 --> 00:00:02,000\n測試內容", encoding="utf-8")

    context = {
        "srt_path": str(srt_path),
        "episode_dir": str(tmp_path),
    }

    # 4. Mock auto_proofread 函數以驗證呼叫
    with patch("auto_proofread.proofread_srt") as mock_proofread:
        mock_proofread.return_value = [{"idx": "1", "text": "校對後內容", "timestamp": "00:00:01,000 --> 00:00:02,000"}]

        # 這裡我們需要 Mock build_context_for_stage 以確保它能從 DB 抓到最新的 Task (包含 speaker_name)
        # 或者我們手動更新 context
        from pipeline.queue.stage_runner import build_context_for_stage
        full_context = build_context_for_stage(test_session, stage_task)
        full_context.update(context)

        # 執行 stage
        proofread_execute(stage_task, full_context)

        # 5. 驗證 speaker_name 是否傳入 proofread_srt
        args, kwargs = mock_proofread.call_args
        assert kwargs.get("speaker_name") == "慧能大師"

def test_auto_proofread_prompt_injection():
    """驗證 auto_proofread.py 內部是否正確將 speaker_name 注入 Prompt。"""
    from auto_proofread import proofread_chunk

    chunk = [{"idx": "1", "text": "測試字幕"}]
    lecture = "測試講義內容"
    speaker = "慧能大師"

    with patch("auto_proofread.call_api") as mock_api:
        mock_api.return_value = "[1] 校對後"

        # 測試預設 Prompt
        proofread_chunk(chunk, lecture, 1, 1, speaker_name=speaker)

        args, _ = mock_api.call_args
        prompt = args[0]
        assert "當前講者：慧能大師" in prompt
        assert "測試講義內容" in prompt
        assert "[1] 測試字幕" in prompt

        # 測試自定義 Prompt
        custom_prompt = "講者是 {{speaker_name}}，請校對：{{srt_text}}"
        proofread_chunk(chunk, lecture, 1, 1, custom_prompt=custom_prompt, speaker_name=speaker)

        args, _ = mock_api.call_args
        prompt = args[0]
        assert "講者是 慧能大師" in prompt
        assert "[1] 測試字幕" in prompt

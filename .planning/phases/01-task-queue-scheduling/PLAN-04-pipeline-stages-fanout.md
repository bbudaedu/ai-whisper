---
plan: "04"
title: "Pipeline Stage 解耦與 Fan-out 機制"
phase: 1
wave: 1
depends_on:
  - "01"
requirements:
  - QUEUE-04
must_haves:
  truths:
    - 四個 stage 模組存在並可獨立呼叫
    - Stage fan-out：download 完成後自動建立 transcribe stage task
    - Stage fan-out：transcribe 完成後自動建立 proofread stage task
    - Stage fan-out：proofread 完成後自動建立 postprocess stage task
    - Stage 輸出透過 output_payload 儲存並傳遞給下一 stage
    - 第 1 集完成下載即可開始聽打，第 2 集仍在下載
  artifacts:
    - pipeline/queue/stage_runner.py
    - pipeline/stages/__init__.py
    - pipeline/stages/download.py
    - pipeline/stages/transcribe.py
    - pipeline/stages/proofread.py
    - pipeline/stages/postprocess.py
    - tests/test_pipeline_stages.py
  key_links:
    - "pipeline/queue/stage_runner.py (enqueue_next_stage) -> pipeline/queue/repository.py (TaskRepository.create_stage_task)"
    - "pipeline/queue/stage_runner.py (build_context_for_stage) -> pipeline/queue/repository.py (get_previous_stage_output)"
    - "pipeline/stages/download.py -> auto_youtube_whisper.py (download_audio)"
    - "pipeline/stages/transcribe.py -> auto_youtube_whisper.py (run_whisper)"
    - "pipeline/stages/proofread.py -> auto_proofread.py (proofread_srt)"
    - "pipeline/stages/postprocess.py -> auto_postprocess.py (generate_excel_and_docx)"
files_modified:
  - pipeline/queue/stage_runner.py
  - pipeline/stages/__init__.py
  - pipeline/stages/download.py
  - pipeline/stages/transcribe.py
  - pipeline/stages/proofread.py
  - pipeline/stages/postprocess.py
  - tests/test_pipeline_stages.py
autonomous: true
---

# Plan 04: Pipeline Stage 解耦與 Fan-out 機制

## Goal
將 `auto_youtube_whisper.py` 的四個 stage（下載→聽打→校對→排版）解耦為獨立模組，並實作 stage 完成後自動 enqueue 下一 stage 的 fan-out 機制（含 output_payload 傳遞），滿足 QUEUE-04「第 1 集完成下載即可開始聽打，第 2 集仍在下載」的需求。

## Tasks

<task id="04-01">
<title>建立 pipeline/stages 套件與四個 stage adapter 模組</title>
<read_first>
- auto_youtube_whisper.py (現有 download_audio, run_whisper, process_video 函式)
- auto_proofread.py (load_lecture_text, proofread_srt, build_srt)
- auto_postprocess.py (generate_excel_and_docx)
- pipeline/queue/models.py (StageTask / StageType / TaskStatus / output_payload)
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md §Pipeline Stage 並行策略
</read_first>
<action>
1. 建立 `pipeline/stages/__init__.py`：
```python
"""Pipeline stage modules — each stage is an independent unit of work."""
```

2. 建立 `pipeline/stages/download.py`：
```python
"""Download stage — 從 YouTube 下載音訊到集數目錄。

此模組是 auto_youtube_whisper.py 中 download_audio() 的 adapter，
將其包裝為可被 stage_runner 呼叫的介面。
"""
import logging

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行下載 stage。

    Args:
        stage_task: 對應的 StageTask 記錄
        context: 包含執行所需的參數：
            - video_id: str
            - title: str
            - playlist_config: dict (whisper_model, whisper_lang 等)

    Returns:
        dict: 執行結果，包含 audio_path 供下一 stage 使用
    """
    from auto_youtube_whisper import download_audio, get_episode_dir

    video_id = context["video_id"]
    title = context["title"]
    pl_config = context.get("playlist_config", {})
    prefix = pl_config.get("folder_prefix", "T097V")

    episode_dir = get_episode_dir(title, prefix=prefix)
    video = {"id": video_id, "title": title}

    audio_path = download_audio(video, episode_dir)
    if audio_path is None:
        raise RuntimeError(f"下載失敗: {title} ({video_id})")

    logger.info(f"Download stage 完成: {audio_path}")
    return {
        "audio_path": audio_path,
        "episode_dir": episode_dir,
    }
```

3. 建立 `pipeline/stages/transcribe.py`：
```python
"""Transcribe stage — 使用 faster-whisper 進行語音辨識。

此模組是 auto_youtube_whisper.py 中 run_whisper() 的 adapter。
此 stage 需要 GPU，排程器會在執行前取得 gpu_lock。
"""
import logging

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行轉錄 stage。

    Args:
        stage_task: 對應的 StageTask 記錄
        context: 包含：
            - audio_path: str (上一 stage 的輸出，從 output_payload 讀取)
            - episode_dir: str
            - playlist_config: dict

    Returns:
        dict: 包含 srt_path, txt_path
    """
    from auto_youtube_whisper import run_whisper

    audio_path = context["audio_path"]
    episode_dir = context["episode_dir"]
    pl_config = context.get("playlist_config", {})

    whisper_model = pl_config.get("whisper_model", "large-v3")
    whisper_lang = pl_config.get("whisper_lang", "auto")
    whisper_prompt = pl_config.get("whisper_prompt", "")

    result = run_whisper(
        audio_path, episode_dir,
        whisper_model=whisper_model,
        whisper_lang=whisper_lang,
        whisper_prompt=whisper_prompt,
    )
    if result is None:
        raise RuntimeError(f"Whisper 辨識失敗: {audio_path}")

    logger.info(f"Transcribe stage 完成: srt={result['srt']}")
    return {
        "srt_path": result["srt"],
        "txt_path": result["txt"],
        "episode_dir": episode_dir,
    }
```

4. 建立 `pipeline/stages/proofread.py`：
```python
"""Proofread stage — 使用 Gemini API 校對字幕。

此模組是 auto_proofread.py 中 proofread_srt() 的 adapter。
"""
import logging
import os

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行校對 stage。

    Args:
        stage_task: 對應的 StageTask 記錄
        context: 包含：
            - srt_path: str (從前一 stage 的 output_payload 讀取)
            - episode_dir: str
            - playlist_config: dict

    Returns:
        dict: 包含 proofread_srt_path
    """
    from auto_proofread import load_lecture_text, proofread_srt, build_srt

    srt_path = context["srt_path"]
    episode_dir = context["episode_dir"]
    pl_config = context.get("playlist_config", {})

    lecture_pdf = pl_config.get("lecture_pdf", "")
    custom_prompt = pl_config.get("proofread_prompt", "")

    import glob
    pdf_paths = [lecture_pdf] if lecture_pdf and os.path.exists(lecture_pdf) else []
    if not pdf_paths:
        series_dir = os.path.dirname(episode_dir)
        pdfs = glob.glob(os.path.join(series_dir, "*.pdf"))
        if pdfs:
            pdf_paths = sorted(pdfs)

    lecture_text = load_lecture_text(pdf_path=pdf_paths)

    corrected = proofread_srt(srt_path, lecture_text, custom_prompt=custom_prompt)
    if not corrected:
        raise RuntimeError(f"校對失敗: {srt_path}")

    base = os.path.splitext(srt_path)[0]
    proofread_path = f"{base}_proofread.srt"
    with open(proofread_path, "w", encoding="utf-8") as f:
        f.write(build_srt(corrected))

    logger.info(f"Proofread stage 完成: {proofread_path}")
    return {
        "proofread_srt_path": proofread_path,
        "srt_path": srt_path,
        "episode_dir": episode_dir,
    }
```

5. 建立 `pipeline/stages/postprocess.py`：
```python
"""Postprocess stage — 產生 Excel 與 Word 報表。

此模組是 auto_postprocess.py 中 generate_excel_and_docx() 的 adapter。
"""
import logging
import os

from pipeline.queue.models import StageTask

logger = logging.getLogger(__name__)


def execute(stage_task: StageTask, context: dict) -> dict:
    """執行後處理 stage。

    Args:
        stage_task: 對應的 StageTask 記錄
        context: 包含：
            - srt_path: str (原始 srt，從前一 stage output_payload 讀取)
            - episode_dir: str

    Returns:
        dict: 包含 excel_path, docx_paths
    """
    import auto_postprocess

    srt_path = context["srt_path"]
    episode_dir = context["episode_dir"]

    base_name = os.path.splitext(os.path.basename(srt_path))[0]
    result = auto_postprocess.generate_excel_and_docx(episode_dir, base_name)
    if not result:
        raise RuntimeError(f"報表生成失敗: {episode_dir}/{base_name}")

    excel_path, docx_student, docx_ai = result
    logger.info(f"Postprocess stage 完成: excel={excel_path}")
    return {
        "excel_path": excel_path,
        "docx_student_path": docx_student,
        "docx_ai_path": docx_ai,
        "episode_dir": episode_dir,
    }
```

每個 stage 模組遵循統一介面：`execute(stage_task, context) -> dict`，回傳的 dict 會被 stage_runner 存入 `output_payload`，供下一 stage 透過 `get_previous_stage_output` 讀取。
</action>
<files>
- pipeline/stages/__init__.py (new)
- pipeline/stages/download.py (new)
- pipeline/stages/transcribe.py (new)
- pipeline/stages/proofread.py (new)
- pipeline/stages/postprocess.py (new)
</files>
<verify>
<automated>python -c "from pipeline.stages import download, transcribe, proofread, postprocess; print('All stage modules import OK')"</automated>
</verify>
<done>
- pipeline/stages/__init__.py 檔案存在
- pipeline/stages/download.py 包含 def execute(stage_task: StageTask, context: dict)
- pipeline/stages/transcribe.py 包含 def execute(stage_task: StageTask, context: dict)
- pipeline/stages/proofread.py 包含 def execute(stage_task: StageTask, context: dict)
- pipeline/stages/postprocess.py 包含 def execute(stage_task: StageTask, context: dict)
- pipeline/stages/download.py 包含 from auto_youtube_whisper import
- pipeline/stages/transcribe.py 包含 from auto_youtube_whisper import run_whisper
- pipeline/stages/proofread.py 包含 from auto_proofread import
- pipeline/stages/postprocess.py 包含 import auto_postprocess
</done>
</task>

<task id="04-02">
<title>實作 stage_runner.py 與 fan-out 機制（含 output_payload 傳遞）</title>
<read_first>
- pipeline/queue/models.py (StageType / TaskStatus / output_payload / get_output / set_output)
- pipeline/queue/repository.py (TaskRepository — create_stage_task / complete_stage / save_stage_output / get_previous_stage_output)
- pipeline/stages/download.py (execute 介面)
- pipeline/stages/transcribe.py (execute 介面)
- pipeline/stages/proofread.py (execute 介面)
- pipeline/stages/postprocess.py (execute 介面)
- .planning/phases/01-task-queue-scheduling/01-CONTEXT.md §Pipeline Stage 並行策略
</read_first>
<action>
建立 `pipeline/queue/stage_runner.py`：

```python
"""Stage 執行器 — 負責執行 stage 並觸發 fan-out（下一 stage）。

Fan-out 規則：
  download → transcribe
  transcribe → proofread
  proofread → postprocess
  postprocess → (結束，更新父任務狀態)

Stage 間資料傳遞：
  每個 stage 的 execute() 回傳 dict，被存入 output_payload。
  下一 stage 啟動時，_build_context_for_stage 會讀取前一 stage 的 output_payload，
  合併 Task 資訊作為 context 傳入。
"""
import logging
from typing import Optional

from sqlmodel import Session

from pipeline.queue.models import (
    StageTask, StageType, TaskStatus, Task,
)
from pipeline.queue.repository import TaskRepository

logger = logging.getLogger(__name__)

# Stage 執行順序（fan-out 鏈）
STAGE_ORDER: list[StageType] = [
    StageType.DOWNLOAD,
    StageType.TRANSCRIBE,
    StageType.PROOFREAD,
    StageType.POSTPROCESS,
]

# 下一個 stage 的映射
NEXT_STAGE: dict[StageType, Optional[StageType]] = {}
for i, stage in enumerate(STAGE_ORDER):
    if i + 1 < len(STAGE_ORDER):
        NEXT_STAGE[stage] = STAGE_ORDER[i + 1]
    else:
        NEXT_STAGE[stage] = None


def get_next_stage(current_stage: StageType) -> Optional[StageType]:
    """取得下一個 stage。"""
    return NEXT_STAGE.get(current_stage)


def enqueue_next_stage(
    session: Session,
    completed_stage: StageTask,
) -> Optional[StageTask]:
    """Stage 完成後自動建立下一 stage 的任務。

    Args:
        session: DB session
        completed_stage: 剛完成的 StageTask

    Returns:
        新建立的 StageTask，若已是最後 stage 則回傳 None
    """
    next_stage_type = get_next_stage(completed_stage.stage)

    if next_stage_type is None:
        # 最後一個 stage 完成，更新父任務狀態
        repo = TaskRepository(session)
        repo.update_task_status(completed_stage.task_id, TaskStatus.DONE)
        logger.info(
            f"Task #{completed_stage.task_id} 所有 stage 完成，"
            f"狀態更新為 DONE"
        )

        # 如果有父任務，檢查是否所有子任務都完成
        task = repo.get_task_by_id(completed_stage.task_id)
        if task and task.parent_task_id:
            repo.check_and_update_parent_status(task.parent_task_id)

        return None

    repo = TaskRepository(session)
    new_stage = repo.create_stage_task(
        task_id=completed_stage.task_id,
        stage=next_stage_type,
        source=completed_stage.source,
        priority=completed_stage.priority,
        max_retries=completed_stage.max_retries,
    )
    logger.info(
        f"Fan-out: stage #{completed_stage.id} ({completed_stage.stage}) 完成 → "
        f"建立 stage #{new_stage.id} ({next_stage_type})"
    )
    return new_stage


def create_initial_stages(
    session: Session,
    task: Task,
    start_stage: StageType = StageType.DOWNLOAD,
) -> StageTask:
    """為新任務建立初始 stage task。

    預設從 DOWNLOAD 開始。若任務已有音訊檔可從 TRANSCRIBE 開始。

    Args:
        session: DB session
        task: 父任務
        start_stage: 起始 stage

    Returns:
        新建立的初始 StageTask
    """
    repo = TaskRepository(session)
    stage = repo.create_stage_task(
        task_id=task.id,
        stage=start_stage,
        source=task.source,
        priority=task.priority,
        max_retries=task.max_retries,
    )
    logger.info(
        f"Task #{task.id} 建立初始 stage: {start_stage} (stage #{stage.id})"
    )
    return stage


def build_context_for_stage(
    session: Session,
    stage_task: StageTask,
) -> dict:
    """為 stage 建構執行 context。

    合併來源：
    1. Task 本身的資訊（video_id, title, playlist_id）
    2. 前一 stage 的 output_payload（audio_path, srt_path 等）
    3. playlist_config（Phase 2 從 PlaylistManager 取得）

    Returns:
        完整的 context dict 供 stage.execute() 使用
    """
    repo = TaskRepository(session)
    task = repo.get_task_by_id(stage_task.task_id)
    if task is None:
        raise RuntimeError(f"Task #{stage_task.task_id} not found")

    # 基礎 context
    context: dict = {
        "video_id": task.video_id,
        "title": task.title,
        "playlist_id": task.playlist_id,
        "playlist_config": {},  # Phase 2 會從 PlaylistManager 取得
    }

    # 合併前一 stage 的輸出
    prev_output = repo.get_previous_stage_output(task.id, stage_task.stage)
    context.update(prev_output)

    return context
```

設計重點：
- `NEXT_STAGE` 明確定義 fan-out 鏈：download→transcribe→proofread→postprocess
- `enqueue_next_stage` 在前一 stage 完成後自動建立下一 stage 的 pending 任務
- 最後一個 stage (postprocess) 完成後，更新父 Task 狀態為 DONE，並檢查播放清單父任務
- `create_initial_stages` 供任務建立時使用，預設從 download 開始
- 新建的 stage 繼承父 stage 的 source 與 priority，確保內部任務的 stage 也維持高優先權
- **`build_context_for_stage` 合併 Task 資訊 + 前一 stage 的 output_payload**，解決 stage 間資料傳遞
</action>
<files>
- pipeline/queue/stage_runner.py (new)
</files>
<verify>
<automated>pytest -q tests/test_pipeline_stages.py -x</automated>
</verify>
<done>
- pipeline/queue/stage_runner.py 包含 STAGE_ORDER
- pipeline/queue/stage_runner.py 包含 NEXT_STAGE
- pipeline/queue/stage_runner.py 包含 def get_next_stage(
- pipeline/queue/stage_runner.py 包含 def enqueue_next_stage(
- pipeline/queue/stage_runner.py 包含 def create_initial_stages(
- pipeline/queue/stage_runner.py 包含 def build_context_for_stage(
- pipeline/queue/stage_runner.py 包含 get_previous_stage_output
- pipeline/queue/stage_runner.py 包含 check_and_update_parent_status
- pipeline/queue/stage_runner.py 包含 StageType.DOWNLOAD
- pipeline/queue/stage_runner.py 包含 StageType.TRANSCRIBE
- pipeline/queue/stage_runner.py 包含 StageType.PROOFREAD
- pipeline/queue/stage_runner.py 包含 StageType.POSTPROCESS
- pipeline/queue/stage_runner.py 包含 repo.update_task_status(completed_stage.task_id, TaskStatus.DONE)
</done>
</task>

<task id="04-03">
<title>實作 QUEUE-04 的完整測試（含 output_payload 傳遞驗證）</title>
<read_first>
- tests/test_pipeline_stages.py (目前為 stub)
- pipeline/queue/stage_runner.py (enqueue_next_stage / create_initial_stages / build_context_for_stage)
- pipeline/queue/repository.py (TaskRepository / save_stage_output / get_previous_stage_output)
- pipeline/queue/models.py (StageType / TaskStatus / TaskSource / output_payload)
- tests/conftest.py (db_engine / db_session fixture)
</read_first>
<action>
替換 `tests/test_pipeline_stages.py` 中的 stub 為完整測試：

```python
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

    # download stage 完成，儲存 output
    dl = create_initial_stages(db_session, task, StageType.DOWNLOAD)
    repo.save_stage_output(dl.id, {"audio_path": "/tmp/audio.m4a", "episode_dir": "/tmp/ep001"})
    repo.complete_stage(dl.id)
    db_session.refresh(dl)

    # fan-out 到 transcribe
    tr = enqueue_next_stage(db_session, dl)
    assert tr is not None

    # build_context_for_stage 應該包含前一 stage 的 output
    context = build_context_for_stage(db_session, tr)
    assert context["video_id"] == "out1"
    assert context["audio_path"] == "/tmp/audio.m4a"
    assert context["episode_dir"] == "/tmp/ep001"


def test_output_payload_chain(db_session):
    """QUEUE-04: 完整 output 傳遞鏈 — download output → transcribe → proofread。"""
    repo = TaskRepository(db_session)
    task = repo.create_task(title="Chain output", video_id="chain_out")

    # download → output: audio_path
    dl = create_initial_stages(db_session, task, StageType.DOWNLOAD)
    repo.save_stage_output(dl.id, {"audio_path": "/a.m4a", "episode_dir": "/ep"})
    repo.complete_stage(dl.id)
    db_session.refresh(dl)

    # transcribe → reads audio_path, outputs srt_path
    tr = enqueue_next_stage(db_session, dl)
    ctx_tr = build_context_for_stage(db_session, tr)
    assert ctx_tr["audio_path"] == "/a.m4a"

    repo.save_stage_output(tr.id, {"srt_path": "/ep/sub.srt", "txt_path": "/ep/sub.txt", "episode_dir": "/ep"})
    repo.complete_stage(tr.id)
    db_session.refresh(tr)

    # proofread → reads srt_path
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

    # child1 完成全部 stage (simplified: 直接建 postprocess 並完成)
    pp1 = repo.create_stage_task(child1.id, StageType.POSTPROCESS)
    repo.complete_stage(pp1.id)
    db_session.refresh(pp1)
    repo.update_task_status(child1.id, TaskStatus.DONE)

    # child2 尚未完成 → 父任務不應為 DONE
    repo.check_and_update_parent_status(parent.id)
    db_session.refresh(parent)
    assert parent.status != TaskStatus.DONE

    # child2 也完成
    pp2 = repo.create_stage_task(child2.id, StageType.POSTPROCESS)
    repo.complete_stage(pp2.id)
    repo.update_task_status(child2.id, TaskStatus.DONE)

    repo.check_and_update_parent_status(parent.id)
    db_session.refresh(parent)
    assert parent.status == TaskStatus.DONE
```

移除 stub `pytest.skip`，確保所有測試可執行且通過。
</action>
<files>
- tests/test_pipeline_stages.py (modify — replace stubs with real tests)
</files>
<verify>
<automated>pytest -q tests/test_pipeline_stages.py -x</automated>
</verify>
<done>
- tests/test_pipeline_stages.py 不包含 pytest.skip("Stub
- tests/test_pipeline_stages.py 包含 def test_stage_fanout(
- tests/test_pipeline_stages.py 包含 def test_full_fanout_chain(
- tests/test_pipeline_stages.py 包含 def test_output_payload_passing(
- tests/test_pipeline_stages.py 包含 def test_output_payload_chain(
- tests/test_pipeline_stages.py 包含 def test_parallel_episodes(
- tests/test_pipeline_stages.py 包含 def test_get_next_stage(
- tests/test_pipeline_stages.py 包含 def test_fanout_preserves_source_and_priority(
- tests/test_pipeline_stages.py 包含 def test_playlist_parent_done_after_all_children(
- 執行 pytest -q tests/test_pipeline_stages.py 結果全部 passed
</done>
</task>

## Verification

```bash
# QUEUE-04 測試
pytest -q tests/test_pipeline_stages.py

# Stage 模組存在
ls pipeline/stages/download.py pipeline/stages/transcribe.py pipeline/stages/proofread.py pipeline/stages/postprocess.py

# Fan-out 鏈正確
grep "NEXT_STAGE" pipeline/queue/stage_runner.py
grep "build_context_for_stage" pipeline/queue/stage_runner.py
grep "get_previous_stage_output" pipeline/queue/stage_runner.py
```

"""
Pipeline State 測試套件
========================
"""

import pytest
import os
import json
import tempfile

from pipeline.state import PipelineState


@pytest.fixture
def state_file(tmp_path):
    return str(tmp_path / "test_state.json")


@pytest.fixture
def state(state_file):
    return PipelineState(state_file=state_file)


class TestStateTracking:
    def test_initial_state_all_pending(self, state):
        summary = state.get_episode_summary("T097V004")
        assert all(v == "pending" for v in summary.values())
        assert len(summary) == 6

    def test_set_and_get_step_status(self, state):
        state.set_step_status("T097V004", "download", "done")
        assert state.get_step_status("T097V004", "download") == "done"
        assert state.get_step_status("T097V004", "transcribe") == "pending"

    def test_set_step_with_metadata(self, state):
        state.set_step_status("T097V004", "transcribe", "done", output_file="/tmp/test.srt")
        assert state.get_step_status("T097V004", "transcribe") == "done"

    def test_invalid_step_raises(self, state):
        with pytest.raises(ValueError):
            state.set_step_status("T097V004", "invalid_step", "done")

    def test_invalid_status_raises(self, state):
        with pytest.raises(ValueError):
            state.set_step_status("T097V004", "download", "invalid_status")


class TestResumeFromFailed:
    def test_get_failed_steps(self, state):
        state.set_step_status("T097V004", "download", "done")
        state.set_step_status("T097V004", "transcribe", "done")
        state.set_step_status("T097V004", "proofread", "failed", error="503 Service Unavailable")
        failed = state.get_failed_steps("T097V004")
        assert failed == ["proofread"]

    def test_resumable_step(self, state):
        state.set_step_status("T097V004", "download", "done")
        state.set_step_status("T097V004", "transcribe", "done")
        state.set_step_status("T097V004", "proofread", "failed")
        assert state.get_resumable_step("T097V004") == "proofread"

    def test_resumable_step_all_done(self, state):
        for step in PipelineState.STEPS:
            state.set_step_status("T097V004", step, "done")
        assert state.get_resumable_step("T097V004") is None


class TestEpisodeCompletion:
    def test_incomplete_episode(self, state):
        state.set_step_status("T097V004", "download", "done")
        assert not state.is_episode_complete("T097V004")

    def test_complete_episode(self, state):
        for step in PipelineState.STEPS:
            state.set_step_status("T097V004", step, "done")
        assert state.is_episode_complete("T097V004")

    def test_complete_with_skipped(self, state):
        for step in PipelineState.STEPS:
            status = "skipped" if step == "proofread" else "done"
            state.set_step_status("T097V004", step, status)
        assert state.is_episode_complete("T097V004")


class TestPersistence:
    def test_state_persists_to_file(self, state, state_file):
        state.set_step_status("T097V004", "download", "done")
        # Load fresh
        state2 = PipelineState(state_file=state_file)
        assert state2.get_step_status("T097V004", "download") == "done"

    def test_reset_episode(self, state):
        state.set_step_status("T097V004", "download", "done")
        state.reset_episode("T097V004")
        assert state.get_step_status("T097V004", "download") == "pending"

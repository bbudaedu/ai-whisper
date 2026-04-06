---
phase: 09-refinement
plan: 03
subsystem: LLM (Proofread)
tags: [llm, prompt, speaker_name, pipeline]
requires: [09-01]
provides: [LLM-01]
affects: [auto_proofread.py, pipeline/queue/stage_runner.py, tests/v2/test_pipeline_context.py]
tech-stack: [python, sqlmodel, pytest]
key-files: [auto_proofread.py, pipeline/queue/stage_runner.py, tests/v2/test_pipeline_context.py]
decisions:
  - "在 Prompt 中明確區分預設提示詞與講者資訊（speaker_section）"
  - "支援自定義 Prompt 中的 {{speaker_name}} 佔位符"
metrics:
  duration: 15min
  completed_date: "2026-03-29"
---

# Phase 09 Plan 03: LLM (Prompt Enhancement) Summary

## Summary
本計畫完成了講者名稱（`speaker_name`）在校對流程中的端到端整合。現在 AI 校對腳本能夠獲得當前任務的講者資訊，顯著提升專有名詞（如法名、人名）的校對精準度。

## Key Changes

### 1. `auto_proofread.py` 優化
- **Prompt 注入**：新增 `speaker_section`，在發送給 LLM 的 Prompt 中加入「當前講者：{speaker_name}」。
- **自定義 Prompt 支援**：更新自定義 Prompt 處理邏輯，支援 `{{speaker_name}}` 佔位符替換。
- **CLI 參數**：正式啟用 `--speaker-name` 參數，供 Pipeline 呼叫時傳遞。

### 2. Pipeline 串接更新
- **Context 建構**：`stage_runner.py` 的 `build_context_for_stage` 函數現在會從 `Task` 資料庫中抓取 `speaker_name` 並放入 context。
- **參數傳遞**：`pipeline/stages/proofread.py` 已經串接到 `auto_proofread.proofread_srt` 並傳遞 `speaker_name`。

### 3. 測試覆蓋
- **`tests/v2/test_pipeline_context.py`**：
  - `test_proofread_runner_receives_speaker_name`: 驗證 Pipeline 執行時能從 DB 正確提取講者資訊。
  - `test_auto_proofread_prompt_injection`: 驗證 `auto_proofread` 內部的 Prompt 渲染邏輯，確保資訊正確注入給 LLM。

## Deviations from Plan

None - 計畫任務已完整執行，且測試驗證通過。

## Known Stubs

None.

## Self-Check: PASSED
- [x] `auto_proofread.py` 包含 speaker 注入邏輯
- [x] `pipeline/queue/stage_runner.py` 包含 speaker_name 提取
- [x] `pytest tests/v2/test_pipeline_context.py` 全部通過
- [x] 講者資訊能正確渲染至 Prompt

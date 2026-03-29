---
phase: 09-refinement
plan: 02
subsystem: Frontend
tags: [UI, React, SpeakerName]
dependency_graph:
  requires: [09-01]
  provides: [UI-01]
  affects: [TaskTracker.tsx]
tech_stack: [React, Lucide, Axios]
key_files: [web-ui-external/src/pages/TaskTracker.tsx]
decisions:
  - "使用 onBlur 與 Enter 鍵觸發 API 更新，確保操作直覺。"
  - "在展開列中新增編輯區塊，避免主列表過於擁擠。"
  - "編輯狀態（editSpeaker）在收合時自動清除，確保下次展開時顯示最新資料。"
metrics:
  duration: "15m"
  completed_date: "2026-03-29"
---

# Phase 09 Plan 02: Frontend (UI Edit Field) Summary

## Summary
實作了 TaskTracker 頁面的說話者名稱編輯功能。使用者現在可以展開任務列，並在新增的「說話者人名」欄位中進行編輯。編輯完成後，透過點擊外部 (onBlur) 或按下 Enter 鍵，系統會自動呼叫後端 API 持久化變更。

## Key Changes
- **TaskTracker.tsx**:
    - 擴展 `TaskRecord` 介面以包含 `speaker_name`。
    - 實作 `handleUpdateSpeaker` 函數，使用 `PATCH /api/tasks/{task_id}` 更新資料。
    - 在任務展開區域新增具備 `User` 圖示的輸入框。
    - 加入 `updatingSpeakerId` 狀態以在儲存時顯示動畫回饋。
    - 支援 `onBlur` 與 `Enter` 鍵自動儲存。

## Deviations from Plan
- **修復語法錯誤**: 在實作過程中有一個函數閉合與判斷式的錯誤，已在後續編輯中修正。
- **自動清除編輯狀態**: 額外實作了在收合任務列時清除對應的 `editSpeaker` 狀態，確保使用者下次展開時看到的是從 API 重新讀取的最新正確資料。

## Known Stubs
None.

## Self-Check: PASSED
- [x] `web-ui-external/src/pages/TaskTracker.tsx` 已更新。
- [x] Commit `f1ba27a` 已建立並包含相關變更。

---
phase: 03-web-ui
plan: 04
subsystem: web-ui-external
tags:
  - react
  - ui
  - forms
  - submission
key-files:
  - web-ui-external/src/pages/SubmitTask.tsx
  - web-ui-external/src/App.tsx
decisions:
  - Unified the file upload and YouTube submission into a single interface with a toggle.
  - Using FormData for file uploads and JSON payload for YouTube submissions, to align with the Phase 2 API specification.
metrics:
  duration: "4m"
  completed_date: "2026-03-22"
---

# Phase 03 Plan 04: Task Submission Page Summary

Implemented a unified task submission form supporting both file uploads and YouTube URL inputs with metadata configuration.

## Features Implemented
- **Mode Toggle**: Clean toggle between "Upload File" and "YouTube URL" modes.
- **Dynamic Inputs**:
  - Drag-and-drop/file selector for audio/video uploads.
  - Single input field for YouTube URLs with auto-detection hints for single videos vs playlists.
- **Parameters**:
  - Audio Nature selection (會議, 佛學課程).
  - Prompt configuration via text area.
  - Multi-select output format checkboxes (txt, srt, word, excel, json).
- **API Integration**:
  - FormData submission for file uploads (`multipart/form-data`).
  - JSON submission for YouTube URLs (`application/json`).
  - Integrated with `axios` client targeting `/api/tasks/`.
- **UI Feedback**: Success and error message handling, with visual loading state during submission.

## Deviations from Plan
None - plan executed exactly as written.

## Known Stubs
None.

## Self-Check: PASSED
- `web-ui-external/src/pages/SubmitTask.tsx` created and wired.
- Build completes successfully (`cd web-ui-external && npm run build`).
- Form properly handles `multipart/form-data` and `application/json` depending on the input mode.
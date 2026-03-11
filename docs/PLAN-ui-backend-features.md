# PLAN: UI and Backend Features

## 1. Task Overview
Implement new features for UI and Backend:
1. Playlist task list can be expanded to full-screen/full-width view.
2. Status indicator showing exact pipeline step completion (Download -> Whisper -> Proofread -> Reports).
3. Editable playlist parameters, including prompt parameters.
4. "Redo" option for specific episodes.

## 2. Agent Assignments (Minimum 3 for Orchestration)
- `frontend-specialist`: Implement React/Tailwind UI components (modals, progress tracking, full-screen toggle).
- `backend-specialist`: Implement FastAPI endpoints (Update config, Redo/Clear episode artifacts, Detailed status fetch).
- `test-engineer`: Verify API responses and UI logic (Lint, format, API validation).

## 3. Phase Breakdown

### Phase 1: Backend System Updates (`backend-specialist`)
1. **API for Editing Playlist Config**:
   - `PUT /api/playlists/{playlist_id}` to update `config.json` via `PlaylistManager`.
   - Support updating `llm_prompt`, `language`, `lecture_pdf`, etc.
2. **API for "Redo" Episode**:
   - `POST /api/playlists/{playlist_id}/episodes/{video_id}/redo`.
   - Logic: Remove entry from `processed_videos.json` AND/OR delete downstream physical artifacts (`.srt`, `.xlsx`) to force regeneration in the next loop.
3. **API for Exact Status Representation**:
   - Enhance the `/api/dashboard` or a specific playlist status API to check actual physical files (`.wav`, `.txt`, `_proofread.srt`, `.xlsx`) to determine and return the *exact* step (e.g., `download_done`, `whisper_done`, `proofread_done`, `reports_done`).

### Phase 2: Frontend Implementation (`frontend-specialist`)
1. **Full-Screen View (任務管理頁面全版面)**:
   - Add a toggle button in `PlaylistTaskManager.tsx` to hide the sidebar or open the table in a full-screen modal/portal overlay.
2. **Detailed Status UI (狀態顯示)**:
   - Convert the binary "Completed/Pending" tag into a progress indicator or multi-step badge (e.g., `✓ 下載 | ✓ 語音 | ⟳ 校對 | ✗ 報表`).
3. **Editable Parameters (編輯播放清單參數)**:
   - Add an "Edit Config" button opening a modal with a form to update prompts, language, and PDF mapping. Submit fires the `PUT` API.
4. **Redo Button (每集重做選項)**:
   - Add an action menu (three dots or icon) next to each episode in the table with a "重做 (Redo)" action. Include a confirmation dialog.

### Phase 3: Verification (`test-engineer` & `frontend-specialist`)
- Run API validator script.
- Run UI/UX Audit and Accessibility checks.
- End-to-end local test (Clicking Redo, editing prompt, ensuring pipeline responds).

## 4. Verification Scripts to Execute (Post-Implementation)
- `python .agent/skills/lint-and-validate/scripts/lint_runner.py .`
- `python .agent/skills/api-patterns/scripts/api_validator.py .`
- `python .agent/skills/frontend-design/scripts/ux_audit.py .`

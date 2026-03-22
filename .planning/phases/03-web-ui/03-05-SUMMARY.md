---
phase: 03-web-ui
plan: 05
subsystem: web-ui-external
tags:
  - react
  - frontend
  - hooks
  - polling
  - ui
requires:
  - 03-03
provides:
  - TaskTracker
  - usePolling
affects:
  - App.tsx
tech-stack:
  - React
  - TypeScript
  - Tailwind CSS
  - Lucide React
key-files:
  - web-ui-external/src/hooks/usePolling.ts
  - web-ui-external/src/pages/TaskTracker.tsx
  - web-ui-external/src/App.tsx
key-decisions:
  - "Created usePolling custom hook using generic types to support polling multiple endpoints."
  - "TaskTracker displays a mobile-friendly list with collapsible rows to minimize screen real estate while still providing complex metadata and download links."
  - "Tasks are sorted in descending order of updated_at to bring newest items to the top."
---

# Phase 03 Plan 05: Task Tracking and Polling UI Summary

Implemented the real-time Task Tracking interface for users to monitor their transciption jobs and download completed transcripts.

## Completed Tasks

1. **Task 1: Implement Polling Hook**
   - Created `usePolling.ts` custom hook with generic response typing to make regular API calls using the `axios` client.
   - Cleanly encapsulates `setInterval` logic and avoids memory leaks with a `useEffect` cleanup handler.
   - Provides `manualRefresh` capability for immediate state checking.
   - Tracked with commit `4fcaad0`.

2. **Task 2: Build Task Tracker View**
   - Created `TaskTracker.tsx` rendering a list of tasks.
   - Implemented real-time polling updates.
   - Built a collapsible row UI to show raw source URLs and individual transcript format download links (txt, srt, vtt, json, tsv) alongside the main "Download All (ZIP)" action.
   - Implemented visual status badges using Lucide React icons for all task states (`pending`, `downloading`, `processing`, `done`, `error`).
   - Integrated into the router inside `App.tsx` at the `/track` route.
   - Tracked with commit `5a6100a`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added React Fragment Import**
- **Found during:** Task 2 Build
- **Issue:** Using `<React.Fragment>` required an import that wasn't included natively when replacing standard `<div>`.
- **Fix:** Used standard `React` import.
- **Files modified:** `web-ui-external/src/pages/TaskTracker.tsx`

**2. [Rule 3 - Missing Dependency] date-fns / standard JS date**
- **Found during:** Task 2 implementation
- **Issue:** Needed robust date formatting to fulfill requirement.
- **Fix:** Switched to standard JS `Intl.DateTimeFormat` within `toLocaleString` for simplicity instead of installing a larger library to keep build lightweight.

## Known Stubs

- **Mock UI states**: Currently `/submit`, `/playlists`, and `/settings` are mapped to temporary standard div messages in `App.tsx` router, pending future plan execution.

## Self-Check: PASSED

- FOUND: web-ui-external/src/hooks/usePolling.ts
- FOUND: web-ui-external/src/pages/TaskTracker.tsx
- FOUND: 4fcaad0
- FOUND: 5a6100a

---
status: verifying
trigger: "Investigate why the task tracking page (/track) is showing a blank screen on https://fayi.budaedu.dpdns.org/track."
updated: 2026-03-25T10:20:00Z
---

## Current Focus

hypothesis: The component was crashing due to calling `.substring()` on a numeric `task.id`.
test: Fix the type mismatch and remove the `.substring()` call.
expecting: The page should render correctly.
next_action: Verify the fix.

## Symptoms

expected: The /track page should show a list of tasks with their status and download options.
actual: The page is reported as blank.
errors: TypeError: task.id.substring is not a function (inferred).
reproduction: Navigate to /track.
started: Post v1.0 milestone.

## Eliminated

## Evidence

- timestamp: 2026-03-25T10:05:00Z
  checked: web-ui-external/src/pages/TaskTracker.tsx
  found: The component renders a table if tasks are present or if it's loading. If it's truly blank, it might be a JS crash.
  implication: Need to find where it might crash.
- timestamp: 2026-03-25T10:08:00Z
  checked: api/routers/tasks.py & api/schemas.py
  found: TaskStatusResponse uses TaskStatus enum for status. TaskTracker.tsx interface TaskRecord uses a string literal union.
  implication: Mismatch might exist but unlikely to cause a blank screen unless it's a runtime error in a hook or render.
- timestamp: 2026-03-25T10:15:00Z
  checked: web-ui-external/src/pages/TaskTracker.tsx line 148
  found: `ID: {task.id.substring(0, 8)}...` while `task.id` is a `number` from the API.
  implication: This is a guaranteed runtime crash during render.

## Resolution

root_cause: Runtime JS crash in `TaskTracker.tsx` because it attempted to call `.substring()` on a numeric `task.id`.
fix: Updated `TaskRecord` interface to use `number` for `id`, removed `.substring()` call, and added fallback for `updated_at`.
verification:
files_changed: ["web-ui-external/src/pages/TaskTracker.tsx"]

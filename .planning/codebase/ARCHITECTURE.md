# Architecture

**Analysis Date:** 2026-03-21

## Pattern Overview

**Overall:** Modular Pipeline/Service-Oriented Architecture

**Key Characteristics:**
- Separation of concerns through distinct modules for pipeline processing, API communication, and task management.
- State-driven pipeline management using serialized JSON states.
- Asynchronous execution support for background tasks.
- Hybrid architecture including a Python backend for data processing/API management and a React/TypeScript frontend for user interaction.

## Layers

**Pipeline Layer:**
- Purpose: Orchestrates data processing (transcription, proofreading, task scheduling).
- Location: `pipeline/`
- Contains: Task definitions, scheduling logic, and orchestration state.
- Depends on: API Client, storage, and external services.

**API Integration Layer:**
- Purpose: Manages communication with external APIs (like NotebookLM or generic REST endpoints).
- Location: `pipeline/api_client.py`, `pipeline/notebooklm_client.py`
- Contains: API wrapper clients, request handling, and error response management.

**Backend Services:**
- Purpose: Exposes functionality via servers or CLI tools.
- Location: `api_server.py`, `auto_notebooklm.py`, `auto_youtube_whisper.py`
- Contains: Entry points for various automation workflows and API endpoints.

**Frontend Layer:**
- Purpose: Provides user interface for monitoring and management.
- Location: `web-ui/src/`
- Contains: React components, state management for frontend, and API consumers.

## Data Flow

**Data Pipeline Flow:**

1. **Trigger:** User or automated process triggers a task via CLI or `api_server.py`.
2. **Orchestration:** `pipeline/notebooklm_scheduler.py` schedules and manages the execution flow.
3. **Execution:** Tasks perform operations (transcription, proofreading) using local tools or API clients.
4. **State Persistence:** Task status and results are persisted in JSON or DB files (`notebooklm_queue.json`, `nocturne_memory/my_memory.db`).

**State Management:**
- Application state is largely persisted in JSON files (`pipeline/state.py` handles this) or database files like `my_memory.db`.

## Key Abstractions

**NotebookLM Tasks:**
- Purpose: Encapsulates specific actions on NotebookLM.
- Examples: `pipeline/notebooklm_tasks.py`
- Pattern: Strategy/Command pattern.

**Pipeline State:**
- Purpose: Represents the current status of a multi-stage process.
- Examples: `pipeline/state.py`

## Entry Points

**Main Orchestrator:**
- Location: `auto_notebooklm.py` (and similar `auto_*.py` scripts)
- Triggers: CLI commands or system cron/background workers.
- Responsibilities: Bootstraps the pipeline, loads configuration, and executes top-level workflows.

## Error Handling

**Strategy:** Exception logging and state-based retry mechanisms.

**Patterns:**
- Logging via standard Python logging.
- Retrying tasks based on failure state tracked in JSON queue files.

## Cross-Cutting Concerns

**Logging:** Standard `logging` library used throughout the backend.
**Validation:** Types defined in `web-ui/src/types.ts` and runtime checks in pipeline.
**Authentication:** Environment-based credentials management (via `.env` or config files).

---

*Architecture analysis: 2026-03-21*

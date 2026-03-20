# Architecture

**Analysis Date:** 2026-03-20

## Pattern Overview

**Overall:** Task-driven automation pipeline with a supporting backend service and web interface.

**Key Characteristics:**
- Orchestration: Pipeline tasks are managed through a scheduler (`pipeline/notebooklm_scheduler.py`) and state management (`pipeline/state.py`).
- Decoupling: Core processing logic is separated into specialized scripts in the root directory and the `pipeline/` package.
- API-first: An `api_server.py` provides an interface for external interactions, likely consumed by the `web-ui`.
- Tool-based: Extensive use of custom scripts for automation, data processing, and proofreading.

## Layers

**Orchestration Layer:**
- Purpose: Manages the lifecycle of tasks and workflows.
- Location: `pipeline/`
- Contains: `notebooklm_scheduler.py`, `notebooklm_tasks.py`, `state.py`.
- Depends on: `pipeline/notebooklm_client.py`, `pipeline/api_client.py`.

**Processing Layer:**
- Purpose: Handles data processing, proofreading, and automation logic.
- Location: `root/`, `pipeline/`
- Contains: `auto_youtube_whisper.py`, `auto_proofread.py`, `pipeline/proofreading_engine.py`, `pipeline/proofread_format.py`.
- Used by: `pipeline/notebooklm_tasks.py`.

**API/Interface Layer:**
- Purpose: Provides access to services.
- Location: `api_server.py`, `web-ui/`
- Contains: FastAPI-based server, React-based web dashboard.

## Data Flow

**Task Execution Flow:**
1. User or automated trigger initiates a process (e.g., video processing).
2. `pipeline/notebooklm_scheduler.py` registers the task and updates `pipeline/state.py`.
3. `pipeline/notebooklm_tasks.py` executes specific logic, interacting with external APIs via `pipeline/notebooklm_client.py`.
4. Results and logs are generated and processed by root scripts.

**State Management:**
- Persistent state is stored in JSON files (`notebooklm_queue.json`, `processed_videos.json`) and sometimes embedded in script-local logic.

## Key Abstractions

**Task Engine:**
- Purpose: Abstracting complex processing steps into runnable tasks.
- Examples: `pipeline/notebooklm_tasks.py` defines unit operations for the pipeline.

**Adapters:**
- Purpose: Standardizing interactions with different LLM/service providers.
- Examples: `adapters/GEMINI.md` indicates modular configuration for model providers.

## Entry Points

**Pipeline/Automation:**
- `auto_youtube_whisper.py`: Entry point for whisper-related workflows.
- `auto_notebooklm.py`: Orchestration script for NotebookLM processes.

**API:**
- `api_server.py`: Primary service entry point.

## Error Handling

**Strategy:** Centralized logging and file-based state checks.

**Patterns:**
- Extensive use of logs (`*.log`) to track status.
- Lock files (`*.lock`) used to prevent concurrent execution conflicts (e.g., `gpu_whisper.lock`).

## Cross-Cutting Concerns

**Logging:** Standard Python logging, outputting to various `.log` files.
**Authentication:** Implicit through environment configuration or API keys defined in `config.json`.
**Validation:** Mostly done via script-specific sanity checks and file format validation in `scripts/`.

---

*Architecture analysis: 2026-03-20*

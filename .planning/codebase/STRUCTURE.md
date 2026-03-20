# Codebase Structure

**Analysis Date:** 2026-03-20

## Directory Layout

```
[project-root]/
├── .planning/       # Planning and analysis documentation
├── adapters/        # Service-specific configurations (e.g., Gemini)
├── mnt/             # Mounted storage (NAS)
├── nocturne_memory/ # Local memory subsystem
├── pipeline/        # Core pipeline logic and orchestration
├── scripts/         # Utility scripts (validation, setup)
├── tests/           # Testing framework and suites
├── web-ui/          # React/Vite-based user interface
└── api_server.py    # Main API server entry point
```

## Directory Purposes

**`pipeline/`:**
- Purpose: Orchestrates business logic and task processing.
- Contains: Task schedulers, API clients, and core processing engines.
- Key files: `pipeline/notebooklm_scheduler.py`, `pipeline/notebooklm_tasks.py`.

**`scripts/`:**
- Purpose: Automation of development and maintenance tasks.
- Contains: Validation and setup scripts.
- Key files: `scripts/validate-all.sh`.

**`web-ui/`:**
- Purpose: Frontend dashboard.
- Contains: React components and styling.
- Key files: `web-ui/src/components/`, `web-ui/package.json`.

**`tests/`:**
- Purpose: Regression and unit testing.
- Contains: Comprehensive test suites.
- Key files: `tests/test_notebooklm_e2e.py`.

## Key File Locations

**Entry Points:**
- `api_server.py`: Server entry.
- `auto_youtube_whisper.py`: Workflow entry.

**Configuration:**
- `config.json`: Project settings.
- `model_capabilities.yaml`: Model-specific capability definitions.

**Core Logic:**
- `pipeline/notebooklm_tasks.py`: Task definitions.

## Naming Conventions

**Files:**
- snake_case for scripts and modules (e.g., `auto_notebooklm.py`).
- kebab-case for UI components (e.g., `PlaylistDashboard.tsx`).

**Directories:**
- snake_case for backend and logic modules.
- kebab-case for web components.

## Where to Add New Code

**New Pipeline Task:**
- Implementation: `pipeline/notebooklm_tasks.py`
- Registration: `pipeline/notebooklm_scheduler.py`
- Tests: `tests/test_notebooklm_tasks.py`

**New API Endpoint:**
- Implementation: `api_server.py`

**New Utility:**
- Implementation: `scripts/` or `pipeline/` depending on scope.

---

*Structure analysis: 2026-03-20*

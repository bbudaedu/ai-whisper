# Codebase Structure

**Analysis Date:** 2026-03-21

## Directory Layout

```
[project-root]/
├── .planning/       # Planning and documentation (GSD commands)
├── .gsd/            # GSD workflow configurations
├── .agent/          # Agent-specific workflows and skills
├── pipeline/        # Core pipeline orchestration logic
├── web-ui/          # React-based frontend
├── nocturne_memory/ # Persistence layer and backend memory management
├── tests/           # Test suite (unit, integration, E2E)
├── scripts/         # Utility scripts (setup, validation)
├── adapters/        # Interface/Model definitions
└── [root-files]     # Entry points and configuration
```

## Directory Purposes

**`pipeline/`:**
- Purpose: Contains all core business logic for the automation pipeline (NotebookLM, Whisper, proofreading).
- Key files: `pipeline/notebooklm_scheduler.py`, `pipeline/notebooklm_client.py`.

**`web-ui/`:**
- Purpose: Frontend code for monitoring and controlling the system.
- Key files: `web-ui/src/App.tsx`, `web-ui/src/components/`, `web-ui/src/types.ts`.

**`nocturne_memory/`:**
- Purpose: Backend component for memory/knowledge management with a separate FastAPI structure and DB management.
- Key files: `nocturne_memory/backend/main.py`, `nocturne_memory/my_memory.db`.

**`tests/`:**
- Purpose: Contains unit and end-to-end tests for the entire project.
- Key files: `tests/test_pipeline.py`, `tests/test_notebooklm_client.py`.

## Key File Locations

**Entry Points:**
- `auto_notebooklm.py`: Main trigger for the NotebookLM pipeline.
- `auto_youtube_whisper.py`: Main trigger for Whisper transcription.
- `api_server.py`: API server entry point.

**Configuration:**
- `config.json`: Project-wide settings.
- `web-ui/vite.config.ts`: Frontend build settings.

**Core Logic:**
- `pipeline/notebooklm_tasks.py`: Orchestration of atomic tasks for processing.

**Testing:**
- `tests/`: All testing assets.

## Naming Conventions

**Files:**
- snake_case for Python scripts (`auto_youtube_whisper.py`).
- kebab-case for React components/TSX files (though often PascalCase in `web-ui/src/components/`).

## Where to Add New Code

**New Feature (Pipeline):**
- Implementation: Create a new module in `pipeline/`.
- Tests: Add a corresponding file in `tests/`.

**New Frontend Component:**
- Implementation: `web-ui/src/components/`.
- Data structure: Update `web-ui/src/types.ts`.

**Utilities:**
- Shared helpers: `pipeline/` for logic, `scripts/` for operational tools.

## Special Directories

**`venv/`:**
- Purpose: Python virtual environment.
- Generated: Yes.

**`node_modules/`:**
- Purpose: Node.js dependencies.
- Generated: Yes.

---

*Structure analysis: 2026-03-21*

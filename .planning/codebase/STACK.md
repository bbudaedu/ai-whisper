# Technology Stack

**Analysis Date:** 2026-03-21

## Languages

**Primary:**
- Python 3.x - Used for backend services, automation scripts, and pipeline orchestration.
- TypeScript (web-ui) - Used for the frontend dashboard.

**Secondary:**
- Bash - Used for shell scripts, process management, and simple environment setups.

## Runtime

**Environment:**
- Linux (x86_64, as detected on current host)

**Package Manager:**
- Python: `venv` (virtual environments)
- Node.js (npm): Package manager for web-ui, uses `vite`.
- Lockfile: `auto_youtube_whisper.lock` (Python), `package.json` (Node.js).

## Frameworks

**Core:**
- FastAPI (Python) - Serves the backend API (`api_server.py`).
- React 19 (TypeScript) - Frontend UI (`web-ui/`).
- Vite (TypeScript) - Build tool and dev server for frontend.

**Testing:**
- Python `unittest` (detected as `tests/*.py`)

**Build/Dev:**
- `yt-dlp` - External tool utilized by Python scripts for media downloads.
- `ffmpeg` - Media processing tool used by `yt-dlp` and `auto_youtube_whisper.py`.

## Key Dependencies

**Critical:**
- `faster-whisper` - Used for speech-to-text.
- `openai`/`google-generativeai` (implied) - Used for LLM-based proofreading and summarization.

**Infrastructure:**
- `uvicorn` - ASGI server for FastAPI.

## Configuration

**Environment:**
- `config.json` - Core configuration for all automation tasks.
- `processed_videos.json` - Tracks pipeline status for videos.

**Build:**
- `tsconfig.json` - TypeScript configuration.
- `package.json` - Node project metadata and build scripts.

## Platform Requirements

**Development:**
- CUDA-enabled GPU (required for `faster-whisper` acceleration).
- `node` (for `yt-dlp` metadata fetching).

---

*Stack analysis: 2026-03-21*

## Last Session Summary
Codebase mapping complete.

- **Components Identified**: 6 major components (API, YouTube Automation, Proofreading, Post-processing, Meeting Pipeline, GPU Locking).
- **Dependencies Analyzed**: Full Python and React stack identified.
- **Technical Debt Found**: 4 major items related to naming conventions, log handling, and experimental feature integration.

### Identified Components
1. `api_server.py`: Management API.
2. `auto_youtube_whisper.py`: YouTube Tracking/Transcribe loop.
3. `auto_proofread.py`: Gemini-based correction.
4. `auto_postprocess.py`: Report and document generation.
5. `auto_meeting_process.py`: Local meeting pipeline.
6. `web-ui`: React dashboard.

---
*Mapped by Antigravity on 2026-03-19*

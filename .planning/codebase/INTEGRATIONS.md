# External Integrations

**Analysis Date:** 2026-03-21

## APIs & External Services

**Speech-to-Text:**
- Whisper (Large-v3/v2 via `faster-whisper`) - Used for automated transcriptions (`auto_youtube_whisper.py`).

**LLM/AI Services:**
- Google Gemini (via `auto_proofread.py` and `auto_notebooklm.py`) - Used for proofreading transcripts and generating post-processing content (summaries, infographics, mindmaps).

**Video Platforms:**
- YouTube (via `yt-dlp`) - Source for video/audio downloads.

## Data Storage

**Filesystem:**
- Network Attached Storage (NAS) - `/mnt/nas/Whisper_auto_rum/` - Used for primary audio, text, SRT, and report storage (`auto_youtube_whisper.py`).

**Caching:**
- `processed_videos.json` - Used for tracking processing state.
- `notebooklm_queue.json` - Used for managing NotebookLM tasks.

## Authentication & Identity

**Auth Provider:**
- Custom / SMTP - Email notifications via Gmail SMTP (hardcoded/config-based credentials for notification automation).

## Monitoring & Observability

**Logs:**
- Local log files (`youtube_whisper.log`, `notebooklm.log`, `meeting_process.log`) - Used for operational tracking and API exposure.

## CI/CD & Deployment

**Hosting:**
- Linux VM / Bare Metal - Managed via local scripts and `systemd` (inferred from `api_server.py` execution structure).

## Environment Configuration

**Required env vars:**
- None strictly enforced via `os.environ` patterns in core scripts; primarily driven by `config.json`.

**Secrets location:**
- `config.json` contains API keys and SMTP credentials.

## Webhooks & Callbacks

**Incoming:**
- REST API (FastAPI) at `api_server.py` handles playlist creation, task triggering, and status reporting.

---

*Integration audit: 2026-03-21*

# Codebase Concerns

**Analysis Date:** 2026-03-20

## Tech Debt

**Pipeline Orchestration:**
- Issue: The codebase relies on multiple ad-hoc scripts (`auto_notebooklm.py`, `auto_youtube_whisper.py`, `auto_proofread.py`) that lack unified error handling and state management.
- Files: `auto_notebooklm.py`, `auto_youtube_whisper.py`, `auto_proofread.py`, `pipeline/notebooklm_scheduler.py`
- Impact: Increased maintenance overhead and potential for race conditions or inconsistent states during pipeline execution.
- Fix approach: Gradually migrate orchestration logic into a centralized, resilient job runner or workflow engine within `pipeline/`.

**Configuration Management:**
- Issue: Scattered configuration files and manual migration scripts suggest a lack of structured environment/configuration management.
- Files: `config.json`, `config_migrator.py`, `config.json.bak`
- Impact: Configuration drift and difficulty managing settings across environments.
- Fix approach: Implement a robust configuration loader (e.g., using `pydantic-settings`) and move all configuration to a standard `config/` directory.

## Known Bugs

**GPU Lock Contention:**
- Issue: Periodic failures reported related to GPU resource locking.
- Files: `gpu_lock.py`, `tests/test_gpu_lock.py`
- Trigger: Concurrent access or improper cleanup of lock files.
- Workaround: Manual removal of `.lock` files or manual intervention in `gpu_whisper.lock`.
- Fix approach: Re-implement locking using a more robust mechanism (e.g., file descriptors or distributed locking if expanding).

## Security Considerations

**Configuration and Secrets:**
- Issue: Potential risk of accidental commitment of credentials, although explicitly flagged in rules.
- Files: `.env` (presence detected), `config.json`
- Risk: Exposure of API keys or database connection strings.
- Current mitigation: Git ignore rules and strict rules documentation.
- Recommendations: Ensure all secret values are injected via system environment variables and never stored in `config.json`.

## Performance Bottlenecks

**Pipeline Serialization:**
- Issue: Heavy tasks are sometimes processed serially in `auto_notebooklm.py` despite the existence of `pipeline/notebooklm_scheduler.py`.
- Impact: High latency for full playlist/lecture processing.
- Improvement path: Continue migrating tasks to use the concurrent semaphore-based pipeline implementation found in `pipeline/notebooklm_scheduler.py`.

## Fragile Areas

**PDF Processing:**
- Issue: Relying on raw text files generated from PDF content (`lecture_cache_*.pdf.txt`) is sensitive to OCR quality and formatting variations.
- Files: `lecture_cache_T097S_001.pdf.txt`, `auto_proofread.py`
- Why fragile: Logic for handling proofreading and formatting is highly coupled to specific input text structure.
- Safe modification: Encapsulate PDF parsing into a unified interface with better validation.

## Test Coverage Gaps

**Error Paths:**
- Issue: Limited testing of failure recovery in the pipeline orchestration logic.
- Files: `tests/test_notebooklm_scheduler.py`, `tests/test_pipeline.py`
- Risk: The system may fail silently or leave data in an inconsistent state during network errors or API failures.
- Priority: Medium.

---

*Concerns audit: 2026-03-20*

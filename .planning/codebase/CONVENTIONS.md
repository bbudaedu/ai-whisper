# Coding Conventions

**Analysis Date:** 2026-03-21

## Naming Patterns

**Files:**
- snake_case: `test_notebooklm_client.py`, `notebooklm_client.py`, `auto_youtube_whisper.py`

**Functions/Methods:**
- snake_case: `ask_question`, `increment_quota`, `_call_mcp`, `_next_id`

**Variables:**
- snake_case: `daily_quota`, `npx_command`, `init_msg`, `tool_result`

**Types:**
- PascalCase for Classes: `NotebookLMClient`, `RateLimitError`

## Code Style

**Formatting:**
- Indentation: 4 spaces
- Line Length: Not strictly enforced, but generally readable

**Linting:**
- Not detected

## Import Organization

**Order:**
1. Standard library imports (e.g., `json`, `os`, `sys`, `pathlib`)
2. Third-party imports (e.g., `pytest`)
3. Local/Relative imports (e.g., `from pipeline.notebooklm_client import ...`)

## Error Handling

**Patterns:**
- Custom Exception hierarchy for specialized errors: `NotebookLMError` (base), `RateLimitError`, `AuthenticationError`.
- `try-except` blocks around I/O operations (JSON reading/parsing, subprocess).
- Raising specific errors with descriptive messages.

## Logging

**Framework:** `logging` module

**Patterns:**
- `logger = logging.getLogger(__name__)`
- `logger.debug()` for internal state and diagnostic information.

## Comments

**When to Comment:**
- Module docstrings explaining overall purpose.
- Method docstrings defining parameters, behavior, and exceptions.
- Brief inline comments for logic flows.

**JSDoc/TSDoc:**
- Python docstrings follow standard Python conventions.

## Function Design

**Size:** Modular and small, focusing on specific tasks (loading/saving, building messages, calling subprocess).

**Parameters:** Use type hints for arguments and return types.

---

*Convention analysis: 2026-03-21*

# Codebase Concerns

**Analysis Date:** 2026-03-21

## Tech Debt

**MCP Client Subprocess Management:**
- Issue: `pipeline/notebooklm_client.py` launches a new `npx` process for every single interaction (`_call_mcp`).
- Files: `pipeline/notebooklm_client.py`
- Impact: Substantial overhead for every call, slowing down responsiveness and creating resource churn.
- Fix approach: Implement a persistent subprocess session or keep the server running as a background service.

**Quota Tracking:**
- Issue: Quota tracking in `pipeline/notebooklm_client.py` uses local file I/O (`~/.config/ai-whisper/notebooklm_quota.json`) which is not thread-safe.
- Files: `pipeline/notebooklm_client.py`
- Impact: Potential data corruption if multiple pipeline instances or parallel tasks access/update the quota file simultaneously.
- Fix approach: Implement a simple file lock or move to an in-memory/database-backed approach if concurrency increases.

## Known Bugs

**JSON Parsing Robustness:**
- Issue: `pipeline/notebooklm_client.py` attempts to parse embedded JSON strings from text responses, which often fails if the model returns non-JSON text or incorrectly escaped content.
- Files: `pipeline/notebooklm_client.py`
- Impact: Inconsistent extraction of session IDs, statuses, or answers.
- Fix approach: Define a stricter contract with the MCP server or improve robustness of parsing logic.

## Security Considerations

**Subprocess Environment:**
- Issue: Passing `os.environ` to `subprocess.Popen` in `pipeline/notebooklm_client.py` may inadvertently expose sensitive host environment variables to the `npx` process.
- Files: `pipeline/notebooklm_client.py`
- Risk: Potential for credentials leakage if the MCP server or child tools are compromised or misconfigured.
- Recommendations: Explicitly whitelist only required environment variables (e.g., `PATH`, `HOME`, `LOGIN_EMAIL`).

## Performance Bottlenecks

**Startup Latency:**
- Issue: Relying on `npx notebooklm-mcp` means triggering Node.js startup, installing/checking for updates, and initializing the TypeScript server on every tool call.
- Files: `pipeline/notebooklm_client.py`
- Cause: Overhead of `npx` and runtime initialization.
- Improvement path: Pre-install the MCP server globally or locally and launch the binary directly, rather than using `npx` every time.

## Fragile Areas

**MCP Protocol Interaction:**
- Issue: `_call_mcp` and `_read_response` rely on line-based `stdout` reading and manual stdin flushing.
- Files: `pipeline/notebooklm_client.py`
- Why fragile: Tight coupling to the MCP stdio format means any change in the server's output buffering or logging can break the client parser.
- Test coverage: Limited unit/e2e tests for protocol-level edge cases (e.g., partial lines, disconnected process).

---

*Concerns audit: 2026-03-21*

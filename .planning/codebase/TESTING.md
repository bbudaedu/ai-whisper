# Testing Patterns

**Analysis Date:** 2026-03-21

## Test Framework

**Runner:**
- `pytest`
- Config: Uses defaults (standard)

**Assertion Library:**
- Native `assert` statements

**Run Commands:**
```bash
pytest             # Run all tests
pytest -v          # Verbose mode
```

## Test File Organization

**Location:**
- Separate directory: `tests/`

**Naming:**
- Prefix: `test_*.py`

## Test Structure

**Suite Organization:**
```python
class TestNotebookLMClient:
    def test_ask_question(self, isolated_quota_file):
        # ... logic
```

**Patterns:**
- `pytest.fixture` for recurring dependencies like `isolated_quota_file`, `mock_api_success_response`.
- `unittest.mock` for patching external dependencies like `subprocess` or internal helper methods (`_call_mcp`).

## Mocking

**Framework:** `unittest.mock`

**Patterns:**
```python
@patch("pipeline.notebooklm_client.NotebookLMClient._call_mcp")
def test_successful_question(self, mock_call):
    mock_call.return_value = self._make_success_response("答案")
    # ... assert
```

## Fixtures and Factories

**Test Data:**
- Simple helper methods within test classes to generate mock responses (`_make_success_response`).
- `conftest.py` for shared fixtures (e.g., `sample_srt_content`, `sample_subtitles`).

## Coverage

**Requirements:** None explicitly defined.

## Test Types

**Unit Tests:** Focus on methods like `ask_question`, `increment_quota`, and `get_remaining_quota`.

**Integration/E2E Tests:** Tests like `test_notebooklm_e2e.py` involve real subprocess calls.

## Common Patterns

**Async Testing:** Not explicitly present in current Python codebase.

**Error Testing:**
```python
with pytest.raises(NotebookLMError, match="Cannot find"):
    client._call_mcp("get_health")
```

---

*Testing analysis: 2026-03-21*

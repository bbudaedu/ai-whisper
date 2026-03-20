# Coding Conventions

**Analysis Date:** 2026-03-20

## Naming Patterns

**Files:**
- Snake case for Python files: `pipeline/notebooklm_tasks.py`, `tests/test_notebooklm_tasks.py`.

**Functions:**
- Snake case for functions and methods: `build_prompt()`, `parse_response()`, `get_output_path()`.

**Variables:**
- Snake case for local variables and parameters.
- Uppercase for constants and enum members: `OUTPUT_SUFFIXES`, `OutputType.MINDMAP`.

**Types:**
- Pascal case for classes and Enums: `OutputType`, `TaskResult`.

## Code Style

**Formatting:**
- Generally compliant with standard Python PEP 8 conventions.
- Type hinting is used extensively for function arguments and return types.

**Linting:**
- Not explicitly configured via standard files (e.g., `.eslintrc`), but code follows clear Pythonic structure.

## Import Organization

**Order:**
1. Standard library imports (e.g., `import logging`, `import os`).
2. Third-party imports (e.g., `import pytest`).
3. Local application imports (e.g., `from pipeline.notebooklm_tasks import ...`).

**Path Aliases:**
- No explicit path aliases observed, relative path manipulation used in test files for imports (`sys.path.insert(0, ...)`).

## Error Handling

**Patterns:**
- Use of custom error handling in Enum conversion (`from_str` raises `ValueError`).
- Graceful handling of empty or missing input (e.g., in `parse_response`, `check_existing_outputs`).

## Logging

**Framework:** `logging` (standard library).

**Patterns:**
- Module-level logger `logger = logging.getLogger(__name__)`.
- Log entries added for key operations (e.g., saving output).

## Comments

**When to Comment:**
- Docstrings are used for modules, functions, and classes, following the Google Python Style Guide format.

## Function Design

**Size:** Modular, single-responsibility functions.

**Parameters:** Use of type annotations for clarity.

**Return Values:** Clearly defined types, occasionally using dataclasses (`TaskResult`) to encapsulate results.

## Module Design

**Exports:** Classes and functions are explicitly imported and used.

---

*Convention analysis: 2026-03-20*

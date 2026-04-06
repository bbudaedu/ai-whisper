# Deferred Items

- Full pytest suite failures in NotebookLM modules:
  - tests/test_notebooklm_e2e.py expects 5 outputs, but current OutputType includes 9 (including studio/faq/glossary/infographic variants).
  - tests/test_notebooklm_tasks.py expects non-empty prompts for all OutputType values; studio output types currently return "N/A (Studio Output)".
  - These failures predate current plan changes and are outside the queue/scheduler scope.

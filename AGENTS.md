# NHL Dashboard Agent Instructions

Read these files before making changes:
- `harness/AGENTS.md`
- `harness/SPEC.md`

Project rules:
- Use Python 3.x and Flask.
- Follow TDD: write a failing test first, then the minimal implementation, then refactor.
- Use `pytest` for all tests.
- Add Google-style docstrings to new functions.
- Keep changes focused and avoid unrelated refactors.
- Use the official NHL API for scores, history, and odds unless `harness/SPEC.md` says otherwise.

Testing rules:
- Every new function needs matching test coverage.
- Name tests `test_<function>_<scenario>`.
- Prefer mocking external API calls.

Workflow:
- Keep data-fetching logic modular.
- Prefer clear, small functions with single responsibilities.
- If an issue or task is ambiguous, document the assumption in the change or issue body.

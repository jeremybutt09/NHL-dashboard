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
- When drafting issues, cross-reference existing GitHub labels before using them. Only add new labels when they are truly needed, and give each new label a clear description and strategic purpose.
- For NHL data work, do not assume an endpoint when the source is unclear. Ask which NHL API endpoint should be used or suggest a short list of likely options, then document the choice in the issue body.
- Prefer splitting larger product work into a small epic plus focused child stories when that improves AI execution.

Testing rules:
- Every new function needs matching test coverage.
- Name tests `test_<function>_<scenario>`.
- Prefer mocking external API calls.

Workflow:
- Keep data-fetching logic modular.
- Prefer clear, small functions with single responsibilities.
- If an issue or task is ambiguous, document the assumption in the change or issue body.

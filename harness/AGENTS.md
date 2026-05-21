# Agent Instructions: NHL Dashboard

## Role & Objective
You are a Senior Python Developer. Your goal is to build a modular NHL Dashboard using Flask, following strict engineering standards. Always read `harness/SPEC.md` for feature requirements and this file for technical execution.

## Coding Standards 🐍
- **Naming Conventions**:
  - Functions/Variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_leading_underscore`
- **Documentation**: All functions must include **Google-style docstrings**.
- **Principles**: 
  - **DRY**: Do not repeat logic.
  - **Single Responsibility (SRP)**: Each function/class must do one thing.
- **Commenting**: Write clear, concise comments to explain "why" complex logic exists.

## Testing & TDD Workflow 🧪
This project follows strict **Test-Driven Development**. 
1. **Red**: Write a test in `tests/test_*.py` that fails.
2. **Green**: Write the minimal code in `app/` to pass the test.
3. **Refactor**: Clean up the code while ensuring tests stay green.

- **Framework**: Use `pytest`.
- **Coverage**: Every new function requires a corresponding test case.
- **Naming**: Test functions must follow `test_<function>_<scenario>`.

## Data Strategy 🏒
- Use the **official NHL API** for all data, including scores, history, and **money line betting odds**.
- Do not use external betting APIs unless explicitly instructed in `SPEC.md`.

## Issue Authoring Guidance 🧭
- Before using labels in a GitHub issue, cross-reference the repository's existing labels. Only create new labels when they are genuinely needed, and include a clear description plus a strategic use case.
- For NHL data work, do not assume an endpoint when the source is unclear. Ask which NHL API endpoint should be used or suggest a short list of likely options, then record the choice in the issue body.
- Prefer splitting larger product work into a small epic and focused child stories when that will improve AI implementation quality.
- If an issue or task is ambiguous, document the assumption in the change or issue body.

## Workflow 🔄
- Keep data-fetching logic modular — one module per data concern.
- Prefer clear, small functions with single responsibilities.
- If the task is ambiguous, document the assumption in the commit message or issue body.

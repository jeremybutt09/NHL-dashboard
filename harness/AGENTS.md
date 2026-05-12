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
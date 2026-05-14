---
name: tdd-standards
description: TDD workflow and coding standards required by harness/AGENTS.md for every new feature.
metadata:
  type: project
---

Strict TDD: Red → Green → Refactor. Every function needs a test before code.

**Why:** Defined in `harness/AGENTS.md` as a non-negotiable project standard.

**How to apply:** Always write failing tests in `tests/test_*.py` first, then add minimal implementation in `app/`. Run `python3 -m pytest` to verify.

## Naming
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`
- Test functions: `test_<function>_<scenario>`

## Docstrings
All functions require Google-style docstrings (Args, Returns, Raises sections).

## Mock strategy
Use `unittest.mock.patch` on `requests.get` — never hit the real API in tests.

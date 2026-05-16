---
name: Feature Story
about: Create a focused user story for the NHL dashboard
title: "[Feature]: "
labels: ["feature"]
---

## User Story
As a `[type of user]`, I want `[goal]` so that `[benefit]`.

## Context
- Product area:
- Parent issue / epic:
- Relevant files or modules:
- Why this matters:
- Assumptions:
- NHL API source:
  - If the exact endpoint is unclear, ask which NHL API endpoint to use or suggest 2-3 likely candidates before implementation.

## Strict Implementation Checklist
- [ ] Fetch or use the correct NHL API data source.
- [ ] Keep data parsing modular and testable.
- [ ] Keep the implementation focused on the story in this issue.
- [ ] Add or update tests in `tests/test_*.py`.
- [ ] Mock external API calls in tests.
- [ ] Preserve existing behavior when data is missing or partial.

## Do Not
- [ ] Do not assume an endpoint without confirming it when the source is unclear.
- [ ] Do not use an external API unless the issue explicitly says to.
- [ ] Do not mix unrelated UI or refactor work into the story.
- [ ] Do not hardcode values that should come from the NHL API.

## Implementation Notes
- Preferred endpoint or source:
- Expected data shape:
- Fallback behavior:
- Rendering notes:

## Definition of Done
- [ ] Follows the repo's Flask and Python conventions.
- [ ] New functions include Google-style docstrings.
- [ ] Tests are written with `pytest`.
- [ ] New functionality has matching test coverage.
- [ ] External API calls are mocked in tests.
- [ ] Change is focused and avoids unrelated refactors.
- [ ] Feature works end-to-end in the dashboard.
- [ ] Important assumptions are documented.

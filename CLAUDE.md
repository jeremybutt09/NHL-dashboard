# NHL Dashboard — Claude Code Instructions

## Read these first

Before making any changes, read:
- `harness/AGENTS.md` — coding standards, TDD workflow, naming conventions
- `harness/SPEC.md` — product vision and MVP feature list

## Project summary

Flask-based NHL scores and betting odds dashboard. Python 3.x, pytest, official NHL public API. No external betting APIs unless SPEC.md says otherwise.

## Mandatory workflow for every change

1. **Red** — write a failing test in `tests/test_*.py`
2. **Green** — write minimal code in `app/` to pass it
3. **Refactor** — clean up, confirm all tests still pass

## Commit format

```
<short description> (Issue #N)

Closes #N
```

## Interactive session permissions

`.claude/settings.json` pre-approves common low-risk tools (file reads/writes, pytest, safe git commands) so developers are not interrupted by repetitive permission prompts during normal work. Destructive operations (`rm -rf`, force-push, hard reset) are explicitly denied. Do not add blanket `Bash` approval to this file.

## Automated issue processing

To run all open GitHub issues sequentially through Claude Code (headless):

```bash
./scripts/process-issues.sh
```

To start from a specific issue number (e.g., after a failure at #7):

```bash
./scripts/process-issues.sh 7
```

Each run opens a fresh Claude session per issue, commits, and closes the issue on GitHub before moving on. See `scripts/issue-prompt.md` for the per-session instructions Claude receives.

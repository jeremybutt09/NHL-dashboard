# Resume Guide

## Clean restart (new session or after a gap)

**Step 1** — verify the environment and quality gate:
```bash
./init.sh
```
This installs backend deps and runs `pytest tests/`. All tests must pass before new work.

**Step 2** — orient yourself:
```bash
cat session-handoff.md
```
Documents last closed issue, MVP status, and known open questions.

**Step 3** — find next work:
```bash
cat feature_list.json
gh issue list --state open --limit 20
```
Pick the lowest-numbered open issue and follow `scripts/issue-prompt.md`.

---

## Resuming process-issues.sh after a usage limit

## Normal resume (script handles it automatically)

Just re-run the script — it picks up from where it left off:

```bash
./scripts/process-issues.sh
```

The script auto-detects partial work (stashes uncommitted changes, skips issues
already committed) before re-running Claude on the interrupted issue.

---

## Manual quick check (if you want to inspect state before resuming)

### 1. Check for uncommitted changes
```bash
git status
```
- **Clean output** → safe to resume, nothing to do.
- **Modified/untracked files** → Claude wrote code but didn't commit. You can
  either let the script stash it automatically, or discard it yourself:
  ```bash
  git stash   # save it out of the way
  # or
  git checkout .   # discard it
  ```

### 2. Check if Claude already committed for the interrupted issue
```bash
git log --oneline -10
```
- **No commit mentioning the issue** → Claude was interrupted before committing.
  Resume normally; Claude will redo the work from scratch.
- **Commit present (e.g. "Add score display (Issue #26)")** → Claude finished
  the code but didn't close the issue on GitHub. The script handles this
  automatically, but you can also do it manually:
  ```bash
  gh issue close 26
  ./scripts/process-issues.sh 27   # start from the next one
  ```

---

## Exit codes from process-issues.sh

| Code | Meaning |
|------|---------|
| `0`  | All issues processed successfully |
| `1`  | Claude error or issue not closed — needs manual investigation |
| `2`  | Usage limit reached — resume when limit resets |

---

## Useful one-liners

```bash
# See what issue the progress file is pointing to
cat .claude-issues-progress

# Clear progress and start over
./scripts/process-issues.sh --reset

# Auto-wait and retry on rate limit (good for overnight runs)
./scripts/process-issues.sh --wait

# Check all open issues remaining
gh issue list --state open --json number,title --jq '.[] | "#\(.number) \(.title)"'

# View log from a specific issue run
ls logs/issues/
cat logs/issues/issue-26-*.log
```

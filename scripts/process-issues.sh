#!/usr/bin/env bash
# Processes open GitHub issues sequentially using Claude Code (headless).
# Saves progress after each issue so the script auto-resumes if interrupted.
#
# Usage:
#   ./scripts/process-issues.sh              # process all open issues (auto-resumes)
#   ./scripts/process-issues.sh 7            # start from issue #7
#   ./scripts/process-issues.sh --wait       # sleep and retry when rate-limited
#   ./scripts/process-issues.sh --reset      # clear saved progress, start from beginning
#   ./scripts/process-issues.sh --help       # show this help

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_TEMPLATE="$REPO_ROOT/scripts/issue-prompt.md"
PROGRESS_FILE="$REPO_ROOT/.claude-issues-progress"
LOG_DIR="$REPO_ROOT/logs/issues"

# Retry settings for --wait mode
RETRY_WAIT_SECS=300   # 5 minutes between retries
MAX_RETRIES=5

# --- Argument parsing ---------------------------------------------------------

WAIT_ON_LIMIT=false
RESET=false
START_FROM=0

for arg in "$@"; do
  case "$arg" in
    --wait)  WAIT_ON_LIMIT=true ;;
    --reset) RESET=true ;;
    --help|-h)
      sed -n '2,10p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    [0-9]*) START_FROM="$arg" ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

# --- Dependency checks --------------------------------------------------------

for cmd in claude gh; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' CLI not found."
    [[ "$cmd" == "claude" ]] && echo "  Install: https://claude.ai/code"
    [[ "$cmd" == "gh"     ]] && echo "  Install: https://cli.github.com"
    exit 1
  fi
done

if [[ ! -f "$PROMPT_TEMPLATE" ]]; then
  echo "ERROR: Prompt template not found at $PROMPT_TEMPLATE"
  exit 1
fi

# --- State management ---------------------------------------------------------

if [[ "$RESET" == true ]]; then
  rm -f "$PROGRESS_FILE"
  echo "Progress state cleared. Starting from the beginning."
fi

# Auto-resume from progress file if no explicit start was given
if [[ "$START_FROM" -eq 0 && -f "$PROGRESS_FILE" ]]; then
  LAST_DONE=$(cat "$PROGRESS_FILE")
  START_FROM=$((LAST_DONE + 1))
  echo "Auto-resuming from Issue #$START_FROM (last completed: #$LAST_DONE)"
fi

mkdir -p "$LOG_DIR"

# --- Helpers ------------------------------------------------------------------

# Returns 0 (true) if the output looks like a Claude usage/rate-limit error.
is_rate_limited() {
  grep -qi \
    "usage limit\|rate.limit\|quota exceeded\|too many requests\|usage_exceeded\|overloaded\|529" \
    <<< "$1"
}

# Runs Claude on the prompt file, capturing output to a log.
# Sets CLAUDE_EXIT to the exit code (never triggers set -e abort).
run_claude() {
  local prompt_file="$1"
  local log_file="$2"
  CLAUDE_EXIT=0
  claude -p "$(<"$prompt_file")" --dangerously-skip-permissions \
    >"$log_file" 2>&1 || CLAUDE_EXIT=$?
  # Always echo to terminal so the user can watch progress
  cat "$log_file"
}

# --- Issue processing ---------------------------------------------------------

cd "$REPO_ROOT"

ISSUES=$(gh issue list \
  --state open \
  --json number,title \
  --jq 'sort_by(.number) | .[] | "\(.number)|\(.title)"')

if [[ -z "$ISSUES" ]]; then
  echo "No open issues found. All done!"
  exit 0
fi

TMPFILE=$(mktemp /tmp/claude-issue-XXXXX.txt)
trap "rm -f '$TMPFILE'" EXIT

PROCESSED=0
SKIPPED=0

while IFS='|' read -r NUMBER TITLE; do

  if [[ "$NUMBER" -lt "$START_FROM" ]]; then
    echo "Skipping Issue #$NUMBER (below start-from threshold $START_FROM)"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  echo ""
  echo "========================================================"
  echo "  Issue #$NUMBER: $TITLE"
  echo "========================================================"
  echo "  Started: $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""

  # --- Pre-issue checks -------------------------------------------------------

  # 1. Stash any uncommitted changes so Claude starts with a clean working tree
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "  Uncommitted changes detected — stashing before starting Issue #$NUMBER..."
    git stash push -m "claude-auto-stash-before-issue-$NUMBER"
    echo "  Stashed. (restore later with: git stash pop)"
    echo ""
  fi

  # 2. Check if Claude already committed work for this issue in a prior interrupted run.
  #    If so, just ensure the issue is closed and advance progress without re-running Claude.
  if git log --oneline | grep -q "Issue #$NUMBER"; then
    echo "  Commit for Issue #$NUMBER already exists in git log."
    STATE=$(gh issue view "$NUMBER" --json state --jq '.state')
    if [[ "$STATE" != "CLOSED" ]]; then
      echo "  Issue was not closed — closing now..."
      gh issue close "$NUMBER"
    fi
    echo "$NUMBER" > "$PROGRESS_FILE"
    PROCESSED=$((PROCESSED + 1))
    echo "  Issue #$NUMBER already done. Advancing."
    continue
  fi

  # ---------------------------------------------------------------------------

  # Build prompt from template
  BODY=$(gh issue view "$NUMBER" --json body --jq '.body')

  sed \
    -e "s/ISSUE_NUMBER/$NUMBER/g" \
    -e "s/ISSUE_TITLE/$(printf '%s' "$TITLE" | sed 's/[\/&]/\\&/g')/g" \
    "$PROMPT_TEMPLATE" > "$TMPFILE"

  BODY_ESCAPED=$(printf '%s' "$BODY" | sed 's/[\/&]/\\&/g; s/$/\\n/' | tr -d '\n')
  sed -i '' "s/ISSUE_BODY/$BODY_ESCAPED/" "$TMPFILE" 2>/dev/null || {
    grep -v "^ISSUE_BODY$" "$TMPFILE" > "${TMPFILE}.tmp" && mv "${TMPFILE}.tmp" "$TMPFILE"
    printf '\n%s\n' "$BODY" >> "$TMPFILE"
  }

  # Run Claude, retrying on rate limits when --wait is set
  CLAUDE_LOG="$LOG_DIR/issue-${NUMBER}-$(date +%Y%m%d-%H%M%S).log"
  ATTEMPT=0

  while true; do
    run_claude "$TMPFILE" "$CLAUDE_LOG"

    if [[ "$CLAUDE_EXIT" -eq 0 ]]; then
      break
    fi

    CLAUDE_OUTPUT=$(cat "$CLAUDE_LOG")

    if is_rate_limited "$CLAUDE_OUTPUT"; then
      if [[ "$WAIT_ON_LIMIT" == true && "$ATTEMPT" -lt "$MAX_RETRIES" ]]; then
        ATTEMPT=$((ATTEMPT + 1))
        echo ""
        echo "Rate limited. Waiting ${RETRY_WAIT_SECS}s then retrying (attempt $ATTEMPT/$MAX_RETRIES)..."
        sleep "$RETRY_WAIT_SECS"
        # Rotate log file for the retry
        CLAUDE_LOG="$LOG_DIR/issue-${NUMBER}-$(date +%Y%m%d-%H%M%S)-retry${ATTEMPT}.log"
        continue
      else
        echo ""
        echo "================================================================"
        echo "  Claude usage limit reached — stopping cleanly."
        echo "  Progress saved at Issue #$NUMBER."
        echo ""
        echo "  When your usage resets, resume with:"
        echo "    ./scripts/process-issues.sh"
        echo "  (or force a specific start: ./scripts/process-issues.sh $NUMBER)"
        echo ""
        echo "  Add --wait to auto-sleep and retry next time:"
        echo "    ./scripts/process-issues.sh --wait"
        echo "================================================================"
        exit 2
      fi
    fi

    # Non-rate-limit failure
    echo ""
    echo "ERROR: Claude exited with code $CLAUDE_EXIT for Issue #$NUMBER."
    echo "Log: $CLAUDE_LOG"
    echo "Fix the problem, then resume with:"
    echo "  ./scripts/process-issues.sh $NUMBER"
    exit 1
  done

  # Verify the issue was actually closed
  STATE=$(gh issue view "$NUMBER" --json state --jq '.state')
  if [[ "$STATE" != "CLOSED" ]]; then
    echo ""
    echo "ERROR: Issue #$NUMBER is still $STATE after Claude finished."
    echo "Log: $CLAUDE_LOG"
    echo "Investigate, close it manually if needed, then resume with:"
    echo "  ./scripts/process-issues.sh $((NUMBER + 1))"
    exit 1
  fi

  # Save progress so the next run auto-resumes from here
  echo "$NUMBER" > "$PROGRESS_FILE"

  PROCESSED=$((PROCESSED + 1))
  echo ""
  echo "  Finished: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "  Issue #$NUMBER closed successfully. (Log: $CLAUDE_LOG)"

done <<< "$ISSUES"

# All done — clear the progress file so a bare re-run starts fresh
rm -f "$PROGRESS_FILE"

echo ""
echo "========================================================"
echo "  Done. Processed: $PROCESSED issue(s). Skipped: $SKIPPED."
echo "========================================================"

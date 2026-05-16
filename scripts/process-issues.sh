#!/usr/bin/env bash
# Processes open GitHub issues sequentially using Claude Code (headless).
# For each issue: runs a fresh Claude session, then verifies the issue is
# closed on GitHub before moving to the next one.
#
# Usage:
#   ./scripts/process-issues.sh           # process all open issues
#   ./scripts/process-issues.sh 7         # start from a specific issue number

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_TEMPLATE="$REPO_ROOT/scripts/issue-prompt.md"
START_FROM="${1:-0}"

# --- Dependency checks -------------------------------------------------------

if ! command -v claude &>/dev/null; then
  echo "ERROR: 'claude' CLI not found. Install Claude Code: https://claude.ai/code"
  exit 1
fi

if ! command -v gh &>/dev/null; then
  echo "ERROR: 'gh' CLI not found. Install the GitHub CLI: https://cli.github.com"
  exit 1
fi

if [[ ! -f "$PROMPT_TEMPLATE" ]]; then
  echo "ERROR: Prompt template not found at $PROMPT_TEMPLATE"
  exit 1
fi

# --- Issue processing --------------------------------------------------------

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

  # Fetch full issue body
  BODY=$(gh issue view "$NUMBER" --json body --jq '.body')

  # Build the prompt: substitute placeholders and append issue details
  sed \
    -e "s/ISSUE_NUMBER/$NUMBER/g" \
    -e "s/ISSUE_TITLE/$(printf '%s' "$TITLE" | sed 's/[\/&]/\\&/g')/g" \
    "$PROMPT_TEMPLATE" > "$TMPFILE"

  # Append raw body after the template (avoids sed escaping the full markdown)
  # The template already has "ISSUE_BODY" as the last line placeholder;
  # replace it with the actual body content.
  BODY_ESCAPED=$(printf '%s' "$BODY" | sed 's/[\/&]/\\&/g; s/$/\\n/' | tr -d '\n')
  sed -i '' "s/ISSUE_BODY/$BODY_ESCAPED/" "$TMPFILE" 2>/dev/null || {
    # Fallback: just append if in-place sed fails on this platform
    grep -v "^ISSUE_BODY$" "$TMPFILE" > "${TMPFILE}.tmp" && mv "${TMPFILE}.tmp" "$TMPFILE"
    printf '\n%s\n' "$BODY" >> "$TMPFILE"
  }

  # Run Claude non-interactively on this issue
  claude -p "$(<"$TMPFILE")" --dangerously-skip-permissions

  # Verify the issue was closed on GitHub
  STATE=$(gh issue view "$NUMBER" --json state --jq '.state')
  if [[ "$STATE" != "CLOSED" ]]; then
    echo ""
    echo "ERROR: Issue #$NUMBER is still $STATE after Claude finished."
    echo "Investigate, close it manually if needed, then re-run:"
    echo "  ./scripts/process-issues.sh $((NUMBER + 1))"
    exit 1
  fi

  PROCESSED=$((PROCESSED + 1))
  echo ""
  echo "  Finished: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "  Issue #$NUMBER closed successfully."

done <<< "$ISSUES"

echo ""
echo "========================================================"
echo "  Done. Processed: $PROCESSED issue(s). Skipped: $SKIPPED."
echo "========================================================"

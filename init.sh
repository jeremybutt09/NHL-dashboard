#!/usr/bin/env bash
# Single entry-point: install backend deps and run the harness quality gate.
# Usage: ./init.sh
set -e

VENV="nhl-dashboard/backend/.venv"
REQS="nhl-dashboard/backend/requirements.txt"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

pip install -r "$REQS" -q

python3 -m pytest tests/ "$@"

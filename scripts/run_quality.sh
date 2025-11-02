#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

REPORT_DIR="$PROJECT_ROOT/reports"
REPORT_FILE="$REPORT_DIR/quality-summary.md"
mkdir -p "$REPORT_DIR"
if [[ ! -f "$REPORT_FILE" ]]; then
  cat > "$REPORT_FILE" <<'EOF'
# Quality Summary

| Timestamp (UTC) | Pytest | Ruff |
|-----------------|--------|------|
EOF
fi

echo "Running pytest..."
pytest
PYTEST_STATUS="pass"

echo "Running ruff..."
ruff check .
RUFF_STATUS="pass"

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
{
  printf '| %s | %s | %s |\n' "$timestamp" "$PYTEST_STATUS" "$RUFF_STATUS"
} >> "$REPORT_FILE"

echo "Quality checks completed."

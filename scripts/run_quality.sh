#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Running pytest..."
pytest

echo "Running ruff..."
ruff check .

echo "Quality checks completed."

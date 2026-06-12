#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[smoke] $*"
}

fail() {
  echo "[smoke] ERROR: $*" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command not found: $1"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TMP_DIR="$(mktemp -d)"
BOOK_DIR=""
BOOKORBIT_ENV_CREATED=0

cleanup() {
  if [[ -n "${BOOK_DIR}" && -d "${BOOK_DIR}" ]]; then
    rm -rf "${BOOK_DIR}"
  fi
  if [[ "${BOOKORBIT_ENV_CREATED}" == "1" ]]; then
    rm -f "${ROOT_DIR}/docker/bookorbit/.env"
  fi
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

require_cmd docker
require_cmd python3
require_cmd find
require_cmd wc

if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose plugin is required (docker compose ...)"
fi

if [[ ! -f "${ROOT_DIR}/docker/bookorbit/.env" ]]; then
  cp "${ROOT_DIR}/docker/bookorbit/.env.example" "${ROOT_DIR}/docker/bookorbit/.env"
  BOOKORBIT_ENV_CREATED=1
fi

log "Validating docker compose files"
for compose_file in "${ROOT_DIR}"/docker/*/docker-compose.yml; do
  docker compose -f "${compose_file}" config -q
done

log "Checking Python syntax"
python3 -m py_compile \
  "${SCRIPT_DIR}/generate_books.py" \
  "${SCRIPT_DIR}/monitor.py" \
  "${SCRIPT_DIR}/generate_comparison.py"

log "Checking monitor CLI options"
monitor_help="$(python3 "${SCRIPT_DIR}/monitor.py" --help)"
if ! grep -q -- "--idle-window" <<<"${monitor_help}"; then
  fail "monitor.py help output missing --idle-window"
fi
if ! grep -q -- "--min-duration" <<<"${monitor_help}"; then
  fail "monitor.py help output missing --min-duration"
fi

log "Extracting local Chart.js bundle from reference/comparison.html"
CHARTJS_FILE="${TMP_DIR}/chart.umd.min.js"
python3 - "${ROOT_DIR}/reference/comparison.html" "${CHARTJS_FILE}" <<'PY'
import re
import sys
from pathlib import Path

in_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
html = in_path.read_text(encoding="utf-8", errors="replace")
match = re.search(r"<script>\s*(.*?)\s*</script>", html, re.DOTALL)
if not match:
    raise SystemExit("No inline script block found in reference/comparison.html")
out_path.write_text(match.group(1), encoding="utf-8")
PY

if [[ ! -s "${CHARTJS_FILE}" ]]; then
  fail "Failed to extract local Chart.js bundle"
fi

log "Generating a tiny synthetic book set"
SMOKE_COUNT="$(( ( $(date +%s) % 89 ) + 11 ))"
while [[ -d "${ROOT_DIR}/books/books_${SMOKE_COUNT}" ]]; do
  SMOKE_COUNT="$((SMOKE_COUNT + 1))"
done
BOOK_DIR="${ROOT_DIR}/books/books_${SMOKE_COUNT}"

python3 "${SCRIPT_DIR}/generate_books.py" "${SMOKE_COUNT}" >/dev/null

generated_epubs="$(find "${BOOK_DIR}" -type f -name '*.epub' | wc -l | tr -d '[:space:]')"
if [[ "${generated_epubs}" != "${SMOKE_COUNT}" ]]; then
  fail "Expected ${SMOKE_COUNT} EPUBs, found ${generated_epubs}"
fi

log "Building offline comparison report from reference data"
SMOKE_REPORT="${TMP_DIR}/comparison_smoke.html"
python3 "${SCRIPT_DIR}/generate_comparison.py" \
  --reports-dir "${ROOT_DIR}/reference" \
  --chartjs-file "${CHARTJS_FILE}" \
  --output "${SMOKE_REPORT}" >/dev/null

if [[ ! -s "${SMOKE_REPORT}" ]]; then
  fail "Comparison report was not generated"
fi
if ! grep -q "Load Test Benchmark - Cross-App Comparison" "${SMOKE_REPORT}"; then
  fail "Generated comparison report does not contain expected title"
fi

log "Smoke test passed"

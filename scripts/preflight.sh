#!/usr/bin/env bash
set -euo pipefail

# Preflight mirrors CI locally so you (or Codex) can iterate to green before a PR.
# Usage:
#   scripts/preflight.sh           # check-only (fails on issues)
#   scripts/preflight.sh --fix     # auto-fix format, then re-run checks
#
# Notes:
# - Respects .gitleaks.toml for doc placeholders.
# - Skips tools that are missing (prints a note) so you can add them incrementally.
# - Uses "changed Python files" for format checks when possible; otherwise whole repo.

MODE="${1:-check}"   # "check" or "--fix"
FIX=0; [[ "${MODE}" == "--fix" ]] && FIX=1

# Determine changed python files vs main for lighter format passes
BASE_SHA="${BASE_SHA:-$(git merge-base origin/main HEAD 2>/dev/null || echo '')}"
HEAD_SHA="${HEAD_SHA:-$(git rev-parse HEAD)}"
if [[ -n "$BASE_SHA" ]]; then
  mapfile -t PY_CHANGED < <(git diff --name-only --diff-filter=ACMR "$BASE_SHA" "$HEAD_SHA" -- '*.py' || true)
else
  mapfile -t PY_CHANGED < <(git ls-files '*.py')
fi
FILES_TRIMMED="$(printf '%s\n' "${PY_CHANGED[@]:-}" | tr '\n' ' ' | xargs || true)"

echo "Preflight mode: $([[ $FIX -eq 1 ]] && echo fix || echo check)"
echo "Changed Python files: ${FILES_TRIMMED:-}"

run_or_note () {
  local name="$1"; shift
  if command -v "${1%% *}" >/dev/null 2>&1; then
    echo ">> $name"
    bash -lc "$*"
  else
    echo "!! Skipping $name (tool not installed): $1"
  fi
}

# Formatting
if [[ $FIX -eq 1 ]]; then
  run_or_note "Black (fix)" "black ${FILES_TRIMMED:-.}"
  run_or_note "isort (fix)" "isort --profile black ${FILES_TRIMMED:-.}"
else
  if [[ -n "$FILES_TRIMMED" ]]; then
    run_or_note "Black (check)" "black --check --diff -- $FILES_TRIMMED"
    run_or_note "isort (check)" "isort --profile black --check-only --diff -- $FILES_TRIMMED"
  else
    echo "No Python file changes; skipping Black/isort checks."
  fi
fi

# Lint / Types
run_or_note "Ruff" "ruff check ."
run_or_note "MyPy" "mypy ."

# Security
run_or_note "Bandit" "bandit -r . -x tests"
run_or_note "Semgrep" "semgrep --error --config auto || semgrep --config p/ci --error"
run_or_note "pip-audit" "pip-audit -r requirements.txt || true"

# Secret scanning (uses .gitleaks.toml allowlist for docs)
if command -v gitleaks >/dev/null 2>&1; then
  run_or_note "Gitleaks" "gitleaks detect --redact --no-git --source . --config .gitleaks.toml"
else
  echo "!! Skipping Gitleaks (not installed). You can run via pre-commit instead."
fi

# Tests
if command -v pytest >/dev/null 2>&1; then
  echo ">> Pytest (quick)"
  pytest -q
else
  echo "!! Skipping pytest (not installed)."
fi

echo "Preflight complete."

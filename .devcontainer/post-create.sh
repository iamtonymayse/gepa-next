#!/usr/bin/env bash
set -euo pipefail

# ensure uv is installed
if ! command -v uv >/dev/null 2>&1; then
    pip install uv
fi

# sync dependencies
uv sync --upgrade

# install pre-commit hooks
pre-commit install

# copy env file if not present
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    cp .env.example .env
fi

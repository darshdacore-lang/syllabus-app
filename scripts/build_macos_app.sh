#!/usr/bin/env zsh
set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)/.."
python3 scripts/build_macos_app.py

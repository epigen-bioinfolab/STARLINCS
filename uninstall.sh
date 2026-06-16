#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
CLI_FILE="$HOME/.local/bin/starlincs"
SHARE_DIR="$HOME/.local/share/starlincs/install_path"

GREEN='\033[0;32m'; RED='\033[0;31m'; RESET='\033[0m'

ok() { echo -e "${GREEN}✔ $1${RESET}"; }
fail() { echo -e "${RED}✗ $1${RESET}"; }

echo "Uninstalling STARLINCS environment..."

if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    ok "Removed virtual environment (.venv)"
else
    fail "No virtual environment found"
fi

# Remove global CLI launcher
if [ -f "$CLI_FILE" ]; then
    rm -f "$CLI_FILE"
    ok "Removed global command (starlincs)"
fi

# Remove install path
if [ -f "$SHARE_DIR" ]; then
    rm -f "$SHARE_DIR"
    ok "Removed install path"
fi

find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "Uninstallation complete ✔"

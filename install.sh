#!/bin/bash
# ────────────────────────────────────────────────────────────────
# STARLINCS Universal Installer Wrapper
# Detects OS and calls the correct platform‑specific installer.
# ────────────────────────────────────────────────────────────────

set -e

# Colours for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}  ✔  $1${RESET}"; }
info() { echo -e "${CYAN}  →  $1${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠  $1${RESET}"; }
fail() { echo -e "${RED}  ✗  $1${RESET}"; exit 1; }

echo -e "${BOLD}STARLINCS — Platform Detection${RESET}"

# Detect OS
OS="$(uname -s 2>/dev/null || echo 'Windows')"
case "$OS" in
    Linux*)
        INSTALL_SCRIPT="install-linux.sh"
        info "Detected Linux."
        ;;
    Darwin*)
        INSTALL_SCRIPT="install-mac.sh"
        info "Detected macOS."
        ;;
    MINGW*|CYGWIN*|MSYS*|Windows_NT)
        INSTALL_SCRIPT="install-wsl.sh"
        info "Detected Windows (Git Bash / WSL)."
        ;;
    *)
        fail "Unsupported operating system: $OS"
        ;;
esac

# Check if the installer script exists
if [ ! -f "$INSTALL_SCRIPT" ]; then
    fail "Installer script '$INSTALL_SCRIPT' not found in the current directory."
fi

# Ensure it is executable (on Unix‑like systems)
if [ "$OS" != "Windows_NT" ] && [ ! -x "$INSTALL_SCRIPT" ]; then
    warn "$INSTALL_SCRIPT is not executable – fixing permissions…"
    chmod 755 "$INSTALL_SCRIPT"
    ok "Permissions fixed."
fi

# Run the platform‑specific installer, passing along any arguments
info "Launching $INSTALL_SCRIPT $* …"
echo ""
exec "./$INSTALL_SCRIPT" "$@"

#!/bin/bash
# ════════════════════════════════
#  STARLINCS — Installer
#  Run once after downloading.
# ════════════════════════════════

set -e

TOOL_NAME="STARLINCS"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
ICON_PATH="$SCRIPT_DIR/assets/icon.png"
LOG_FILE="$(pwd)/starlincs_install.log"

# ── Colours (terminal only — stripped from log) ──────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Logging setup ────────────────────────────────────────────────────
# All output (stdout + stderr) is tee'd into the log file from the start.
# The log file contains plain text (no ANSI codes); the terminal gets colours.
# We open the log early so even a crash in step 1 is captured.

# Strip ANSI escape codes before writing to the log
_log_filter() { sed 's/\x1b\[[0-9;]*m//g'; }

# Redirect: terminal sees raw output (colours); log sees clean text
exec > >(tee >(_log_filter >> "$LOG_FILE")) 2>&1

# Write a clear session header now that tee is running
{
  echo "=================================================="
  echo "  STARLINCS Installer"
  echo "  Started   : $(date)"
  echo "  User      : $USER"
  echo "  Host      : $(hostname)"
  echo "  Directory : $(pwd)"
  echo "  Script    : $SCRIPT_DIR"
  echo "  Log file  : $LOG_FILE"
  echo "=================================================="
  echo ""
} | tee /dev/stderr >/dev/null   # write header to log via the pipe above

# Trap: on any unexpected exit, mark the log so you know it was abnormal
trap 'echo ""; echo "!! INSTALLER EXITED UNEXPECTEDLY (exit code $?) at line $LINENO" ' ERR

ok()   { echo -e "${GREEN}  ✔  $1${RESET}"; }
info() { echo -e "${CYAN}  →  $1${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠  $1${RESET}"; }
step() { echo -e "\n${BOLD}$1${RESET}"; }
fail() {
    echo -e "${RED}  ✗  $1${RESET}"
    echo ""
    echo "!! INSTALL FAILED: $1"
    echo "   See full log: $LOG_FILE"
    exit 1
}

# ── Banner ───────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║                    STARLINCS  —  Installer                   ║"
echo "  ║   Signature-driven Transcriptome Alignment for Repurposing   ║"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Step 1/7: Python ─────────────────────────────────────────────────
step "[1/7]  Checking Python 3…"
PYTHON=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>&1 | awk '{print $2}')
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
            PYTHON=$(command -v "$cmd")
            ok "Found $cmd  ($VER)  →  $PYTHON"
            break
        fi
    fi
done
[ -z "$PYTHON" ] && fail "Python 3.8+ not found. Install with:  sudo apt install python3"

# ── Step 2/7: tkinter ────────────────────────────────────────────────
step "[2/7]  Checking tkinter (GUI library)…"
if ! "$PYTHON" -c "import tkinter" 2>/dev/null; then
    warn "tkinter not found — installing…"
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y python3-tk   || fail "Could not install python3-tk. Try:  sudo apt install python3-tk"
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3-tkinter  || fail "Could not install tkinter. Try:  sudo dnf install python3-tkinter"
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm tk        || fail "Could not install tk. Try:  sudo pacman -S --noconfirm tk"
    elif command -v zypper &>/dev/null; then
        sudo zypper install -y python3-tk    || fail "Could not install tkinter. Try:  sudo zypper install -y python3-tk"
    elif command -v apk &>/dev/null; then
        sudo apk add python3-tkinter         || fail "Could not install tkinter. Try:  sudo apk add python3-tkinter"
    else
        fail "Cannot install tkinter automatically. Please install it manually for your distro."
    fi
fi
ok "tkinter is available"

# ── Step 3/7: Virtual environment ────────────────────────────────────
step "[3/7]  Setting up Python virtual environment…"
if [ -d "$VENV_DIR" ]; then
    info "Removing old virtual environment…"
    rm -rf "$VENV_DIR"
fi
"$PYTHON" -m venv "$VENV_DIR" || fail "Failed to create virtual environment."
ok "Virtual environment created at $VENV_DIR"

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# ── Step 4/7: Python packages ─────────────────────────────────────────
step "[4/7]  Installing Python packages…"
info "Upgrading pip…"
"$VENV_PIP" install --upgrade pip -q

PACKAGES=("pandas" "gseapy" "numpy" "openpyxl")
for pkg in "${PACKAGES[@]}"; do
    if "$VENV_PYTHON" -c "import $pkg" 2>/dev/null; then
        ok "$pkg already installed"
    else
        info "Installing $pkg…"
        "$VENV_PIP" install "$pkg" || fail "Failed to install $pkg"
        ok "$pkg installed"
    fi
done

# ── Step 5/7: CLI entry point ─────────────────────────────────────────
step "[5/7]  Creating command-line entry point…"
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

SHARE_DIR="$HOME/.local/share/starlincs"
mkdir -p "$SHARE_DIR"
echo "$SCRIPT_DIR" > "$SHARE_DIR/install_path"
ok "Install path saved to $SHARE_DIR/install_path"

cat > "$LOCAL_BIN/starlincs" <<'WRAPPER'
#!/bin/bash
POINTER="$HOME/.local/share/starlincs/install_path"

if [ ! -f "$POINTER" ]; then
    echo "STARLINCS: cannot find install path. Please re-run install.sh." >&2
    exit 1
fi

SCRIPT_DIR="$(cat "$POINTER")"

if [ ! -d "$SCRIPT_DIR" ]; then
    echo "STARLINCS: install directory '$SCRIPT_DIR' no longer exists." >&2
    echo "  → Move the folder back, or re-run install.sh from the new location." >&2
    exit 1
fi

VENV_PY="$SCRIPT_DIR/.venv/bin/python"
CLI="$SCRIPT_DIR/cli.py"

exec "$VENV_PY" "$CLI" "$@"
WRAPPER

chmod +x "$LOCAL_BIN/starlincs"
ok "Launcher created at $LOCAL_BIN/starlincs"


# ── Fonts: Install Roboto family ─────────────────────────────────────
step "[6/7] Installing Roboto fonts…"

FONT_SRC="$SCRIPT_DIR/resources/fonts"
FONT_DST="$HOME/.local/share/fonts/starlincs"

if [ ! -d "$FONT_SRC" ]; then
    warn "Font folder not found: $FONT_SRC"
else
    mkdir -p "$FONT_DST"

    info "Copying Roboto fonts to user font directory…"
    cp "$FONT_SRC"/*.ttf "$FONT_DST/" 2>/dev/null || true

    info "Refreshing font cache (fc-cache)…"
    fc-cache -f "$HOME/.local/share/fonts" >/dev/null 2>&1 || true

    ok "Roboto fonts installed"
fi

# ── PATH persistence ──────────────────────────────────────────────────
step "[7/7] Installing PATH persistence"
export PATH="$HOME/.local/bin:$PATH"
grep -q '\.local/bin' "$HOME/.bashrc" 2>/dev/null \
    || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    grep -q '\.local/bin' "$HOME/.zshrc" 2>/dev/null \
        || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
fi
hash -r 2>/dev/null || true
ok "~/.local/bin added to PATH"

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║         Installation Complete!  ✔        ║"
echo "  ╚══════════════════════════════════════════╝"

# Launch GUI immediately using the full path (no PATH needed)
if [ -x "$HOME/.local/bin/starlincs" ]; then
    echo -e "  ${BOLD}Starting STARLINCS GUI now...${RESET}"
    echo ""
    "$HOME/.local/bin/starlincs" gui &
else
    echo -e "  ${YELLOW}Launcher not found at $HOME/.local/bin/starlincs${RESET}"
fi

echo ""
echo -e "  ${BOLD}For future use:${RESET}"
echo -e "  • Open a ${BOLD}new terminal${RESET} and run:  ${CYAN}starlincs gui${RESET}"
echo ""
echo "  Full install log saved to: $LOG_FILE"
echo ""

#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Description:
#   Syncs the current project directory into the uniccass-icdesign-tools
#   shared_xserver folder, excluding heavy artifacts. Then optionally starts
#   the Docker/X11 IC design tools environment.
#
# Usage:
#   cd /path/to/your/project
#   ./sync_and_start.sh
#
# Assumptions:
#   - uniccass-icdesign-tools lives as a sibling of the project directory
#     (i.e. both are under the same parent folder).
#   - The script is run FROM the project directory (or PROJECT_SRC is set).
#
# Environment overrides:
#   PROJECT_SRC=...          # project to sync        (default: $PWD)
#   TOOLS_DIR=...            # uniccass-icdesign-tools (auto-detected)
#   SHARED_DIR=...           # shared_xserver path     (auto-detected)
#   START_DOCKER=0|1         # start Docker after sync (default: 1)
#   CLEAN_OLD_CONTAINERS=0|1 # remove old containers   (default: 1)
# ------------------------------------------------------------------------------

# ===== CONFIG (auto-detected, no hardcoded paths) =====

# Project source: wherever you run this script from
PROJECT_SRC="${PROJECT_SRC:-$(pwd)}"
PROJECT_NAME="$(basename "$PROJECT_SRC")"

# Parent directory (where both project and tools dir live)
PARENT_DIR="$(cd "$PROJECT_SRC/.." && pwd)"

# Auto-detect the tools directory (glob for uniccass*icdesign* to be flexible)
if [[ -z "${TOOLS_DIR:-}" ]]; then
  TOOLS_DIR="$(find "$PARENT_DIR" -maxdepth 1 -type d -iname '*uniccass*icdesign*' | head -n1 || true)"
  if [[ -z "$TOOLS_DIR" ]]; then
    echo "ERROR: Could not find a uniccass-icdesign-tools directory in: $PARENT_DIR"
    echo "  Make sure it is at the same level as your project, or set TOOLS_DIR manually."
    exit 1
  fi
fi

SHARED_DIR="${SHARED_DIR:-$TOOLS_DIR/shared_xserver}"

# Destination: directly inside shared_xserver
DEST_DIR="$SHARED_DIR"

# Container mount point (informational)
CONTAINER_SHARED_ROOT="/home/designer/shared"

# Flags
START_DOCKER="${START_DOCKER:-1}"
CLEAN_OLD_CONTAINERS="${CLEAN_OLD_CONTAINERS:-1}"

# ===== CHECKS =====

if [[ ! -d "$PROJECT_SRC" ]]; then
  echo "ERROR: PROJECT_SRC does not exist: $PROJECT_SRC"
  exit 1
fi

if [[ ! -d "$TOOLS_DIR" ]]; then
  echo "ERROR: TOOLS_DIR does not exist: $TOOLS_DIR"
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "ERROR: rsync is not installed."
  echo "  sudo apt-get update && sudo apt-get install -y rsync"
  exit 1
fi

mkdir -p "$DEST_DIR"

# ===== SYNC =====

echo "==> Project:   $PROJECT_SRC"
echo "==> Dest:      $DEST_DIR"
echo "==> Tools dir: $TOOLS_DIR"
echo ""
echo "==> Syncing (excluding heavy artifacts)..."

# rsync options
RSYNC_EXTRA=()
if rsync --help 2>/dev/null | grep -q -- '--ignore-missing-args'; then
  RSYNC_EXTRA+=(--ignore-missing-args)
fi

rsync -av --delete "${RSYNC_EXTRA[@]}" \
  --exclude '.git/' \
  --exclude 'runs/' \
  --exclude '**/runs/' \
  --exclude 'build/' \
  --exclude '*.vcd' \
  --exclude '*.vvp' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'node_modules/' \
  --exclude '*.log' \
  "$PROJECT_SRC"/ "$DEST_DIR"/

echo ""
echo "==> Sync complete."
echo "    Host:      $DEST_DIR"
echo "    Container: $CONTAINER_SHARED_ROOT/"
echo ""

# ===== RUN DOCKER =====

if [[ "$START_DOCKER" == "1" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed or not in PATH."
    exit 1
  fi

  if [[ "$CLEAN_OLD_CONTAINERS" == "1" ]]; then
    existing="$(docker ps -a --format '{{.Names}}' | grep -E '^unic-cass-tools-' || true)"
    if [[ -n "$existing" ]]; then
      echo "==> Removing old unic-cass-tools containers:"
      echo "$existing"
      while read -r n; do
        [[ -n "$n" ]] && docker rm -f "$n" >/dev/null
      done <<< "$existing"
    fi
  fi

  # WSL fix: /dev/dri does not exist, patch Makefile to remove the GPU device flag
  if grep -q 'Microsoft\|microsoft\|WSL' /proc/version 2>/dev/null; then
    if grep -q '/dev/dri' "$TOOLS_DIR/Makefile"; then
      echo "==> WSL detected: patching Makefile to remove --device=/dev/dri:/dev/dri"
      sed -i 's|--device=/dev/dri:/dev/dri||g' "$TOOLS_DIR/Makefile"
    fi
  fi

  echo "==> Starting Docker environment (make start)..."
  cd "$TOOLS_DIR"
  make start
else
  echo "==> START_DOCKER=0, skipping Docker startup."
fi
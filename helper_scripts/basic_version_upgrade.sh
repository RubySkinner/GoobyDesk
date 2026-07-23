#!/bin/bash

# GoobyDesk Upgrade Script
# This script performs a backup and upgrade of the GoobyDesk application

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR=${APP_DIR:-/var/www/GoobyDesk}
SERVICE_NAME=${SERVICE_NAME:-goobydesk.service}
DATA_DIR=${DATA_DIR:-"${APP_DIR}/prod_data"}
LOG_FILE=${LOG_FILE:-/var/log/goobydesk.log}
BACKUP_DIR=${BACKUP_DIR:-/var/tmp}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="prod_data_backup_${TIMESTAMP}.tgz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
DEFAULT_RUNTIME_USER=caddy
RUNTIME_USER=${SUDO_USER:-${RUNTIME_USER:-$DEFAULT_RUNTIME_USER}}

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}========= GoobyDesk Upgrade Script ==========${NC}"
echo -e "${GREEN}=============================================${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo ""

# Check if running as root
if [ "${EUID:-0}" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Ensure required commands
for cmd in git tar mktemp systemctl python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: required command '$cmd' not found"
        exit 1
    fi
done

# Check if app directory exists
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Error: Application directory ${APP_DIR} does not exist${NC}"
    exit 1
fi

# Step 1: Stop service
echo -e "${YELLOW}Step 1/6: Stopping service...${NC}"
systemctl stop "$SERVICE_NAME" || true
echo -e "${GREEN}  ✓ Service stopped (or was not running)${NC}"
echo ""

echo -e "${YELLOW}Step 2/6: Creating backup...${NC}"
BACKUP_TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${BACKUP_TEMP_DIR}"' EXIT
mkdir -p "${BACKUP_TEMP_DIR}/prod_data"

if [ -d "$DATA_DIR" ]; then
    cp -a "$DATA_DIR/"* "${BACKUP_TEMP_DIR}/prod_data/" 2>/dev/null || true
    echo "  - prod_data folder backed up"
else
    echo -e "${YELLOW}  - Warning: prod_data directory not found${NC}"
fi

if [ -f "$LOG_FILE" ]; then
    cp -a "$LOG_FILE" "${BACKUP_TEMP_DIR}/"
    echo "  - goobydesk.log backed up"
else
    echo -e "${YELLOW}  - Warning: log file not found${NC}"
fi

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_PATH" -C "$BACKUP_TEMP_DIR" .
echo -e "${GREEN}  ✓ Backup created: ${BACKUP_PATH}${NC}"
echo ""

echo -e "${YELLOW}Step 3/6: Pulling latest code from git...${NC}"
git -C "$APP_DIR" fetch --all --prune
git -C "$APP_DIR" pull origin main || true
echo -e "${GREEN}  ✓ Code updated (or local changes prevented fast-forward)${NC}"
echo ""

echo -e "${YELLOW}Step 4/6: Updating dependencies...${NC}"
if [ -x "${APP_DIR}/venv/bin/pip" ]; then
    "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
    echo -e "${GREEN}  ✓ Dependencies updated${NC}"
else
    echo -e "${YELLOW}  - Warning: venv pip not found; skipping dependency install${NC}"
fi
echo ""

echo -e "${YELLOW}Step 5/6: Starting service...${NC}"
systemctl start "$SERVICE_NAME"
echo -e "${GREEN}  ✓ Service started${NC}"
echo ""

echo -e "${YELLOW}Step 6: Waiting 10 seconds for service to fully initialize...${NC}"
sleep 10
echo ""

echo -e "${YELLOW}Service Status:${NC}"
systemctl status "$SERVICE_NAME" --no-pager || true
echo ""

echo -e "${YELLOW}Recent Log Entries (last 25 lines):${NC}"
if [ -f "$LOG_FILE" ]; then
    tail -n 25 "$LOG_FILE"
else
    echo "  - Log file not found: ${LOG_FILE}"
fi
echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}============== Upgrade Complete =============${NC}"
echo -e "Backup location: ${GREEN}${BACKUP_PATH}${NC}"
echo -e "${GREEN}=============================================${NC}"

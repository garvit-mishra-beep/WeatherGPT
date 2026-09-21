#!/usr/bin/env bash
# ==============================================================================
# WeatherGPT — Native Production Deployment Helper Script
# ==============================================================================
# Non-destructive deployment and upgrade script for native Linux deployments.
# Usage: ./scripts/deploy_native.sh [/path/to/virtualenv]
# ==============================================================================

set -euo pipefail

VENV_PATH="${1:-/opt/weathergpt/venv}"
SERVICE_NAME="weathergpt.service"

echo "====================================================================="
echo "WeatherGPT Native Production Deployment / Upgrade"
echo "====================================================================="
echo "Python Virtualenv: ${VENV_PATH}"

if [ ! -d "${VENV_PATH}" ]; then
    echo "ERROR: Virtual environment not found at ${VENV_PATH}."
    exit 1
fi

echo "[1/4] Upgrading Python dependencies..."
"${VENV_PATH}/bin/pip" install --quiet --upgrade pip
"${VENV_PATH}/bin/pip" install --quiet -r requirements.txt

echo "[2/4] Executing database migrations (Alembic)..."
"${VENV_PATH}/bin/alembic" upgrade head

echo "[3/4] Validating production configuration..."
"${VENV_PATH}/bin/python" scripts/verify_production_config.py

echo "[4/4] Reloading systemd service..."
if command -v systemctl &> /dev/null; then
    sudo systemctl reload-or-restart "${SERVICE_NAME}"
    echo "Service ${SERVICE_NAME} reloaded successfully."
else
    echo "Notice: systemctl not available in current environment; skipping service restart."
fi

echo "====================================================================="
echo "Deployment completed successfully."
echo "====================================================================="

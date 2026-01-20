#!/bin/bash
# Azure VM deployment script for 1440 Bot backend
# Run this on a fresh Azure VM (Ubuntu/Debian)
# Usage: ./deploy_azure.sh

set -e

echo "=========================================="
echo "  1440 Bot Azure VM Deployment"
echo "=========================================="
echo ""

# Update system packages
echo "Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3-dev python3-venv build-essential poppler-utils libmagic1 tesseract-ocr

# Install uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Create project directory (adjust as needed)
PROJECT_DIR="$HOME/1440_bot"
if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# If code is already cloned, skip
if [ ! -d ".git" ]; then
    echo "Please clone your repository here first:"
    echo "  git clone <your-repo-url> ."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install all dependencies
echo "Installing all dependencies..."
uv pip install -e .

# Create systemd service file
echo "Creating systemd service..."
sudo tee /etc/systemd/system/1440-bot.service > /dev/null <<EOF
[Unit]
Description=1440 Bot FastAPI Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin"
ExecStart=$PROJECT_DIR/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable 1440-bot.service

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "To start the service:"
echo "  sudo systemctl start 1440-bot"
echo ""
echo "To check status:"
echo "  sudo systemctl status 1440-bot"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u 1440-bot -f"
echo ""

#!/bin/bash
# One-command setup script for 1440 Bot backend
# Usage: ./setup.sh

set -e  # Exit on error

echo "=========================================="
echo "  1440 Bot Backend Setup"
echo "=========================================="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
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

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To start the server:"
echo "  python main.py"
echo ""

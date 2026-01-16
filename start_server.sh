#!/bin/bash
# Start script for 1440 Bot backend (Linux/Mac)
# Usage: ./start_server.sh

set -e

echo "Starting 1440 Bot Backend..."
echo ""

# Check if virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run setup first: ./setup.sh"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Please create .env file from env.example"
fi

# Start server
echo "Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Use uvicorn directly for better reliability
uvicorn app.app:app --host 0.0.0.0 --port 8000 --reload

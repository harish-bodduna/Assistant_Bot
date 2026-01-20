# Complete Setup Guide

## ✅ What's Fixed

1. **All dependencies now in `pyproject.toml`**:
   - ✅ `fastapi>=0.115.0`
   - ✅ `uvicorn[standard]>=0.30.0`
   - ✅ `openai>=1.0.0`
   - ✅ `pydantic-settings>=2.0.0`
   - ✅ All other required packages

2. **One-command installation**:
   - Windows: `.\setup.ps1`
   - Linux/Mac: `./setup.sh`

3. **Updated `uv.lock`** - All dependencies locked and ready

## 🚀 Quick Start

### Fresh Installation

1. **Clone repository**
2. **Run setup** (one command):
   ```powershell
   # Windows
   .\setup.ps1
   
   # Linux/Mac
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

4. **Start server**:
   ```powershell
   # Windows
   .\start_server.ps1
   
   # Linux/Mac
   ./start_server.sh
   ```

## 📦 For Azure VM Deployment

See `deploy_azure.sh` - Complete automated deployment script that:
- Installs system dependencies
- Sets up virtual environment
- Installs all Python packages
- Creates systemd service
- Configures auto-start

## 🔧 Manual Installation (if needed)

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv
uv venv .venv

# Activate
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1

# Install all dependencies (ONE COMMAND)
uv pip install -e .
```

## ✅ Verification

After installation, verify:
```bash
python -c "import fastapi, uvicorn, openai; print('✅ All packages installed!')"
python -c "from app.app import app; print('✅ App imports successfully!')"
```

## 🐛 Troubleshooting

### "Module not found" after setup
```bash
uv pip install -e .  # Reinstall all dependencies
```

### Port 8000 in use
```bash
# Find and kill process
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux:
lsof -ti:8000 | xargs kill
```

### Virtual environment issues
```bash
# Delete and recreate
rm -rf .venv  # Linux/Mac
Remove-Item -Recurse -Force .venv  # Windows
./setup.sh  # Run setup again
```

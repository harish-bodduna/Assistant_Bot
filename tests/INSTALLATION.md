# Installation Guide - 1440 Bot Backend

## Quick Start (One Command)

### Windows
```powershell
.\setup.ps1
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

This will:
1. Install `uv` if not present
2. Create virtual environment (`.venv`)
3. Install all dependencies from `pyproject.toml`
4. Ready to run!

## Starting the Server

### Windows
```powershell
.\start_server.ps1
```

### Linux/Mac
```bash
chmod +x start_server.sh
./start_server.sh
```

Or manually:
```bash
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
python main.py
```

## Azure VM Deployment

1. **SSH into your Azure VM**
2. **Clone the repository:**
   ```bash
   git clone <your-repo-url> 1440_bot
   cd 1440_bot
   ```
3. **Run deployment script:**
   ```bash
   chmod +x deploy_azure.sh
   ./deploy_azure.sh
   ```
4. **Configure environment:**
   ```bash
   cp env.example .env
   nano .env  # Edit with your credentials
   ```
5. **Start the service:**
   ```bash
   sudo systemctl start 1440-bot
   sudo systemctl status 1440-bot
   ```

## Dependencies

All dependencies are now properly listed in `pyproject.toml`:
- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **OpenAI** - LLM API client
- **Qdrant Client** - Vector database
- **Azure Storage Blob** - Blob storage
- **Docling** - PDF processing
- And all other required packages

## Troubleshooting

### "Module not found" errors
Run: `uv pip install -e .` to reinstall all dependencies

### Port 8000 already in use
Change port in `main.py` or kill the process:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux
lsof -ti:8000 | xargs kill
```

### Virtual environment issues
Delete `.venv` and run setup again:
```bash
rm -rf .venv  # Linux/Mac
Remove-Item -Recurse -Force .venv  # Windows
./setup.sh  # or .\setup.ps1
```

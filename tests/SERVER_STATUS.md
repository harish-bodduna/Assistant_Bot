# Server Status

## ✅ Server is Running!

The FastAPI server is currently running on **port 8000**.

### Access Points:
- **Health Check:** http://localhost:8000/health
- **API Documentation:** http://localhost:8000/docs
- **Q&A Endpoint:** http://localhost:8000/api/qa/answer
- **Ingestion Endpoint:** http://localhost:8000/api/ingest/blob

### Current Process:
- **Port:** 8000 (LISTENING)
- **Process ID:** Check with `netstat -ano | findstr :8000`

## Starting the Server

### Option 1: Use Start Script (Recommended)
```powershell
# Windows
.\start_server.ps1

# Linux/Mac
./start_server.sh
```

### Option 2: Use Uvicorn Directly
```bash
# Activate virtual environment first
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1

# Start server
uvicorn app.app:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Use main.py
```bash
# Activate virtual environment first
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1

# Start server
python main.py
```

## Troubleshooting

### Server Not Starting?

1. **Check if port is in use:**
   ```powershell
   # Windows
   netstat -ano | findstr :8000
   
   # Linux
   lsof -i:8000
   ```

2. **Kill existing process:**
   ```powershell
   # Windows (replace <PID> with actual process ID)
   taskkill /PID <PID> /F
   
   # Linux
   kill <PID>
   ```

3. **Check for errors:**
   - Run server in foreground to see error messages
   - Check if `.env` file exists and has correct values
   - Verify all dependencies are installed: `uv pip install -e .`

4. **Verify imports:**
   ```bash
   python -c "from app.app import app; print('✅ App loads successfully')"
   ```

### Server Starts But Not Accessible?

1. **Check firewall settings**
2. **Verify host binding:** Should be `0.0.0.0` (all interfaces) or `127.0.0.1` (localhost only)
3. **Try accessing from browser:** http://localhost:8000/docs

## Stopping the Server

- **If running in terminal:** Press `Ctrl+C`
- **If running as background process:**
  ```powershell
  # Find process
   netstat -ano | findstr :8000
   
   # Kill process (replace <PID>)
   taskkill /PID <PID> /F
   ```

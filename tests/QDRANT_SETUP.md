# Qdrant Setup Guide - Persistent Container

## How Qdrant Persists

The Qdrant container is configured to run **persistently**, meaning it will continue running even after you close Cursor or your terminal. Here's how it works:

### Key Settings:
1. **Detached Mode (`-d`)**: Container runs in the background
2. **Restart Policy (`--restart unless-stopped`)**: Container automatically restarts on system reboot (if Docker Desktop is running)
3. **Named Container (`--name qdrant`)**: Easy to manage and reference

## Starting Qdrant

### Option 1: Using Docker Compose (Recommended)
```powershell
docker compose up -d
```

### Option 2: Using the PowerShell Script
```powershell
.\start_qdrant.ps1
```

### Option 3: Direct Docker Command
```powershell
docker run -d --name qdrant --restart unless-stopped -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.9.2
```

## Making Docker Desktop Start Automatically on Boot

For Qdrant to auto-start on system reboot, Docker Desktop must also start automatically:

### Windows Settings:
1. Open **Docker Desktop**
2. Click the **Settings** (gear icon) in the top right
3. Go to **General** settings
4. Enable: **"Start Docker Desktop when you log in"**
5. Click **Apply & Restart**

Alternatively:
1. Press `Win + R`
2. Type `shell:startup` and press Enter
3. Create a shortcut to Docker Desktop in this folder

## Managing Qdrant Container

### Check Status:
```powershell
docker ps --filter "name=qdrant"
```

### View Logs:
```powershell
docker compose logs -f qdrant
# OR
docker logs -f qdrant
```

### Stop Qdrant:
```powershell
docker compose down
# OR
docker stop qdrant
```

### Start Qdrant (if stopped):
```powershell
docker compose up -d
# OR
docker start qdrant
```

### Remove Qdrant (stops and removes container):
```powershell
docker compose down -v
# OR
docker rm -f qdrant
```

## Verify Qdrant is Running

1. **Check container status:**
   ```powershell
   docker ps
   ```

2. **Access Qdrant Dashboard:**
   Open browser: http://localhost:6333/dashboard

3. **Test API:**
   ```powershell
   curl http://localhost:6333/collections
   ```

## Troubleshooting

### Container won't start:
- Make sure Docker Desktop is running
- Check logs: `docker logs qdrant`
- Check if port 6333 is already in use: `netstat -ano | findstr :6333`

### Container stops after closing terminal:
- This shouldn't happen with `-d` flag, but if it does, check Docker Desktop is running
- Verify restart policy: `docker inspect qdrant | Select-String -Pattern "RestartPolicy"`

### Container doesn't auto-start on reboot:
- Ensure Docker Desktop is set to start automatically (see above)
- Check Docker Desktop is actually running after reboot

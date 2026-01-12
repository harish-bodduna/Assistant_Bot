# Script to start Qdrant container with persistence settings
# This container will run in detached mode and persist even after closing Cursor

Write-Host "Starting Qdrant with Docker Compose..." -ForegroundColor Cyan

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "Docker is running." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

# Check if docker-compose is available
try {
    docker compose version | Out-Null
    $useCompose = $true
} catch {
    Write-Host "docker-compose not found, using docker run instead..." -ForegroundColor Yellow
    $useCompose = $false
}

if ($useCompose) {
    # Use docker-compose (recommended)
    Write-Host "Using Docker Compose to start Qdrant..." -ForegroundColor Green
    docker compose up -d
    
    Start-Sleep -Seconds 3
    
    # Verify it's running
    $running = docker ps --filter "name=qdrant" --format "{{.Names}}" 2>$null
    if ($running -eq "qdrant") {
        Write-Host "`nQdrant started successfully!" -ForegroundColor Green
        docker ps --filter "name=qdrant" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        Write-Host "`nQdrant is running at: http://localhost:6333" -ForegroundColor Cyan
        Write-Host "Dashboard: http://localhost:6333/dashboard" -ForegroundColor Cyan
    } else {
        Write-Host "ERROR: Failed to start Qdrant container" -ForegroundColor Red
        docker compose logs qdrant
        exit 1
    }
} else {
    # Fallback to docker run
    Write-Host "Using docker run to start Qdrant..." -ForegroundColor Yellow
    
    # Check if container already exists
    $containerExists = docker ps -a --filter "name=qdrant" --format "{{.Names}}" 2>$null
    
    if ($containerExists -eq "qdrant") {
        Write-Host "Qdrant container already exists. Checking status..."
        $status = docker ps --filter "name=qdrant" --format "{{.Status}}" 2>$null
        if ($status) {
            Write-Host "Qdrant is already running!" -ForegroundColor Green
            docker ps --filter "name=qdrant" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        } else {
            Write-Host "Starting existing Qdrant container..." -ForegroundColor Yellow
            docker start qdrant
            Start-Sleep -Seconds 2
            docker ps --filter "name=qdrant" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            Write-Host "Qdrant started successfully!" -ForegroundColor Green
        }
    } else {
        Write-Host "Creating and starting new Qdrant container..." -ForegroundColor Yellow
        
        # Start Qdrant with:
        # -d: detached mode (runs in background)
        # --name qdrant: name the container
        # --restart unless-stopped: auto-restart on boot/reboot (unless manually stopped)
        # -p 6333:6333 -p 6334:6334: port mappings
        docker run -d --name qdrant --restart unless-stopped -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.9.2
        
        Start-Sleep -Seconds 3
        
        # Verify it's running
        $running = docker ps --filter "name=qdrant" --format "{{.Names}}" 2>$null
        if ($running -eq "qdrant") {
            Write-Host "Qdrant started successfully!" -ForegroundColor Green
            docker ps --filter "name=qdrant" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            Write-Host "`nQdrant is running at: http://localhost:6333" -ForegroundColor Cyan
            Write-Host "Dashboard: http://localhost:6333/dashboard" -ForegroundColor Cyan
        } else {
            Write-Host "ERROR: Failed to start Qdrant container" -ForegroundColor Red
            docker logs qdrant
            exit 1
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "PERSISTENCE SETTINGS:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "* Container runs in detached mode" -ForegroundColor Green
Write-Host "* Restart policy: unless-stopped" -ForegroundColor Green
Write-Host "* Will continue running after closing Cursor/terminal" -ForegroundColor Green
Write-Host "* Will auto-start on system reboot (if Docker Desktop auto-starts)" -ForegroundColor Green
Write-Host "`nTo stop: docker compose down (or: docker stop qdrant)" -ForegroundColor Gray
Write-Host "To view logs: docker compose logs -f qdrant (or: docker logs -f qdrant)" -ForegroundColor Gray

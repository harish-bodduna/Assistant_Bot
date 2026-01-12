# Simple script to test Qdrant connection
$ProgressPreference = 'SilentlyContinue'

Write-Host "Testing Qdrant connection..." -ForegroundColor Cyan

try {
    $response = Invoke-WebRequest -Uri "http://localhost:6333/collections" -UseBasicParsing
    Write-Host "SUCCESS: Qdrant API is responding!" -ForegroundColor Green
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Could not connect to Qdrant" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nMake sure Qdrant is running: docker ps --filter name=qdrant" -ForegroundColor Yellow
}

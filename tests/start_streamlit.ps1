# Script to start Streamlit Chat UI
$env:Path = "C:\Users\Harish\.local\bin;$env:Path"
.\1440_env\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD;$PWD\src"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

# Load environment variables from .env
Get-Content .env | ForEach-Object {
    $p=$_ -split '=',2
    if($p.Length -eq 2 -and $p[0].Trim() -ne '' -and $p[1].Trim() -ne '') {
        $val = $p[1].Trim()
        if($val -match '^["''](.+)["'']$') {
            $val = $val.Trim('"', "'")
        }
        set-item -path "env:$($p[0].Trim())" -value $val
    }
}

Write-Host "`n=== Starting Streamlit Chat UI ===" -ForegroundColor Cyan
Write-Host "Server will be available at: http://localhost:8501" -ForegroundColor Green
Write-Host "`nPress Ctrl+C to stop the server.`n" -ForegroundColor Yellow

streamlit run ui/chat.py --server.port 8501

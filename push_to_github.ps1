# Script to push changes to GitHub on branch "office_day1"
# Prerequisites: Git must be installed and available in PATH

Write-Host "=== Pushing to GitHub branch 'office_day1' ===" -ForegroundColor Cyan

# Check if Git is available
$gitCheck = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCheck) {
    Write-Host "ERROR: Git is not found in PATH." -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "Or add Git to your PATH if it's already installed." -ForegroundColor Yellow
    exit 1
}

# Check if this is a git repository
if (-not (Test-Path .git)) {
    Write-Host "Initializing git repository..." -ForegroundColor Yellow
    git init
    git remote add origin https://github.com/harish-bodduna/Assistant_Bot.git
}

# Create and switch to the new branch
Write-Host "`nCreating branch 'office_day1'..." -ForegroundColor Yellow
git checkout -b office_day1 2>$null
if ($LASTEXITCODE -ne 0) {
    # Branch might already exist, try to switch to it
    git checkout office_day1
}

# Add all changes
Write-Host "`nStaging all changes..." -ForegroundColor Yellow
git add .

# Commit changes
Write-Host "`nCommitting changes..." -ForegroundColor Yellow
$commitMessage = "Office day 1: Updates and improvements"
git commit -m $commitMessage

# Push to remote
Write-Host "`nPushing to GitHub (branch: office_day1)..." -ForegroundColor Yellow
git push -u origin office_day1

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Successfully pushed to GitHub branch 'office_day1'!" -ForegroundColor Green
    Write-Host "Repository: https://github.com/harish-bodduna/Assistant_Bot/tree/office_day1" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Push failed. You may need to:" -ForegroundColor Red
    Write-Host "  1. Set up authentication (GitHub CLI or SSH keys)" -ForegroundColor Yellow
    Write-Host "  2. Check your internet connection" -ForegroundColor Yellow
    Write-Host "  3. Verify you have push access to the repository" -ForegroundColor Yellow
}

# build-and-run.ps1
# Automates building the frontend, exporting python requirements, building the local Docker image, and running the container.

# Stop on error
$ErrorActionPreference = "Stop"

# 1. Build frontend
Write-Host "=== Building frontend ===" -ForegroundColor Cyan
Set-Location frontend
npm install
npm run build
Set-Location ..

# 2. Export Python requirements using uv if available
Write-Host "=== Exporting python requirements ===" -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv export --no-hashes --no-dev -o requirements.txt
} else {
    Write-Host "uv not found, skipping requirements.txt export (using existing requirements.txt)" -ForegroundColor Yellow
}

# 3. Clean up existing container if it exists
Write-Host "=== Cleaning up existing downtify-local container ===" -ForegroundColor Cyan
$existing = docker ps -a --filter "name=downtify-local" --format "{{.Names}}"
if ($existing -eq "downtify-local") {
    Write-Host "Stopping and removing existing container..."
    docker stop downtify-local
    docker rm downtify-local
}

# 4. Build local Docker image
Write-Host "=== Building Docker image (downtify:local) ===" -ForegroundColor Cyan
docker build -t downtify:local .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed!"
    exit 1
}

# 5. Create local docker directories
Write-Host "=== Creating data & downloads directories ===" -ForegroundColor Cyan
$null = New-Item -ItemType Directory -Force -Path ./docker/downloads
$null = New-Item -ItemType Directory -Force -Path ./docker/data

# 6. Run container
Write-Host "=== Running Docker container ===" -ForegroundColor Cyan
docker run -d `
  --name downtify-local `
  -p 8000:8000 `
  -v "${PWD}/docker/downloads:/downloads" `
  -v "${PWD}/docker/data:/data" `
  downtify:local

Write-Host "`n=== Success! Downtify is running at http://localhost:8000 ===" -ForegroundColor Green

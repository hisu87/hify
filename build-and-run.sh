#!/bin/bash
set -e

# build-and-run.sh
# Automates building the frontend, exporting python requirements, building the local Docker image, and running the container.

# 1. Build frontend
echo "=== Building frontend ==="
cd frontend
npm install
npm run build
cd ..

# 2. Export Python requirements using uv if available
echo "=== Exporting python requirements ==="
if command -v uv &> /dev/null; then
    uv export --no-hashes --no-dev -o requirements.txt
else
    echo "uv not found, skipping requirements.txt export (using existing requirements.txt)"
fi

# 3. Clean up existing container if it exists
echo "=== Cleaning up existing downtify-local container ==="
if [ "$(docker ps -a -q -f name=downtify-local)" ]; then
    echo "Stopping and removing existing container..."
    docker stop downtify-local
    docker rm downtify-local
fi

# 4. Build local Docker image
echo "=== Building Docker image (downtify:local) ==="
docker build -t downtify:local .

# 5. Create local docker directories
echo "=== Creating data & downloads directories ==="
mkdir -p ./docker/downloads ./docker/data

# 6. Run container
echo "=== Running Docker container ==="
docker run -d \
  --name downtify-local \
  -p 8000:8000 \
  -v "$(pwd)/docker/downloads:/downloads" \
  -v "$(pwd)/docker/data:/data" \
  downtify:local

echo -e "\n=== Success! Downtify is running at http://localhost:8000 ==="

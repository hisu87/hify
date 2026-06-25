---
icon: lucide/box
---

# Local Docker Build & Test

If you are contributing to Downtify and want to test your changes inside a Docker container locally, you need to manually build the image.

The `Dockerfile` requires both the frontend compiled assets (`frontend/dist`) and a synced `requirements.txt`.

## 🚀 Quick Start (Automated Script)

Two scripts are provided in the root directory to automate the entire process (building the frontend, exporting requirements, stopping/removing any existing container, building the docker image, and starting a new container):

- **Windows (PowerShell):**

  ```powershell
  ./build-and-run.ps1
  ```

- **Linux/macOS/Git Bash:**
  
  ```bash
  chmod +x build-and-run.sh
  ./build-and-run.sh
  ```

---

## 🛠️ Manual Steps

If you prefer to perform the steps manually:

## 1. Prepare dependencies

Before building the Docker image, ensure the frontend is built and the Python dependencies are exported.

### Build the frontend

The Docker image copies the `frontend/dist` directory. You must build it first:

```bash
cd frontend
npm install
npm run build
cd ..
```

### Export Python requirements

Downtify uses `uv` for dependency management. The Dockerfile expects a `requirements.txt` file, which is generated from `uv.lock`.
You can use the provided Makefile to export it:

```bash
make export
```

_(If you don't have `make`, run: `uv export --no-hashes --no-dev -o requirements.txt`)_

## 2. Build the Docker Image

Once the `frontend/dist` directory and `requirements.txt` are ready, build the image. You can tag it as `downtify:local`:

```bash
docker build --load -t downtify:local .
```

## 3. Run the container locally

Create local directories for downloads and database storage to prevent cluttering your filesystem, then run the container using your new image:

**Mac/Linux (Bash/Zsh):**

```bash
# Create directories
mkdir -p ./docker/downloads ./docker/data

# Run the container
docker run -d \
  --name downtify-local \
  -p 8000:8000 \
  -v $(pwd)/docker/downloads:/downloads \
  -v $(pwd)/docker/data:/data \
  downtify:local
```

**Windows (PowerShell):**

```powershell
# Create directories
mkdir ./docker/downloads, ./docker/data -ErrorAction SilentlyContinue

# Run the container
docker run -d `
  --name downtify-local `
  -p 8000:8000 `
  -v ${PWD}/docker/downloads:/downloads `
  -v ${PWD}/docker/data:/data `
  downtify:local
```

You can now open **[http://localhost:8000](http://localhost:8000)** in your browser to test your local build!

## 4. Cleaning up

When you are done testing, you can stop and remove the container:

```bash
docker stop downtify-local && docker rm downtify-local
```

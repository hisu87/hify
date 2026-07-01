---
icon: lucide/download
---

# Installation

The quickest way to run Hify is with a single `docker run` command. No Python, Node.js or other system dependencies needed on the host — everything is bundled inside the image.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running

## Docker run

```bash
docker run -d \
  --name hify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v hify_data:/data \
  --restart unless-stopped \
  ghcr.io/hisu87/hify
```

Replace `/path/to/music` with the directory where you want your music saved.

Once the container starts, open **[http://localhost:8000](http://localhost:8000)** in your browser.

## Volumes

| Volume | Purpose |
|--------|---------|
| `/downloads` | Downloaded audio files |
| `/data` | Application database and persistent settings |

Both volumes persist across container restarts and upgrades. The `/downloads` volume can be any directory on your host machine or a named Docker volume.

## Custom port

To expose Hify on a different host port, change the left side of `-p`:

```bash
docker run -d \
  --name hify \
  -p 9090:8000 \           # host:container
  -v /path/to/music:/downloads \
  -v hify_data:/data \
  ghcr.io/hisu87/hify
```

Then open **[http://localhost:9090](http://localhost:9090)**.

## Updating

Pull the latest image and recreate the container:

```bash
docker pull ghcr.io/hisu87/hify
docker stop hify && docker rm hify
docker run -d --name hify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v hify_data:/data \
  --restart unless-stopped \
  ghcr.io/hisu87/hify
```

Your music and settings are preserved in the volumes.

## What's next?

- **[Docker Compose](docker-compose.md)** — easier way to manage the container long-term
- **[Environment variables](environment-variables.md)** — tune anti-bot behaviour and other advanced options
- **[Download settings](../features/download-settings.md)** — choose your format and bitrate

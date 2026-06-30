---
icon: lucide/file-code
---

# Docker Compose

Docker Compose is the recommended way to run Hify for persistent home-server setups. It makes updates, backups and configuration changes easy.

## Minimal setup

Create a `docker-compose.yml` file:

```yaml
services:
  hify:
    container_name: hify
    image: ghcr.io/hisu87/hify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - hify_data:/data
    restart: unless-stopped

volumes:
  hify_data:
```

Start it:

```bash
docker compose up -d
```

Open **[http://localhost:8000](http://localhost:8000)**.

## Custom port

If port 8000 is already in use, map a different host port and set the `HIFY_PORT` environment variable so the container listens on the same port internally:

```yaml
services:
  hify:
    image: ghcr.io/hisu87/hify:latest
    ports:
      - '9090:30321'
    environment:
      - HIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - hify_data:/data
    restart: unless-stopped
```

## With custom DNS (recommended)

Some ISPs and corporate networks block YouTube. Adding explicit DNS resolvers improves reliability:

```yaml
services:
  hify:
    image: ghcr.io/hisu87/hify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - hify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## Updating

```bash
docker compose pull
docker compose up -d
```

Your music and settings are preserved in the volumes.

## Volumes

| Path inside the compose file | Purpose |
|------------------------------|---------|
| `./downloads:/downloads` | Downloaded audio files (local directory) |
| `hify_data:/data` | Application database and settings (named volume) |

You can replace the named volume with a local path (`./data:/data`) if you prefer to manage it yourself.

# Stage 1: build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: build backend dependencies
FROM python:3.13-alpine AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --root-user-action ignore -r requirements.txt

FROM python:3.13-alpine

LABEL maintainer="hisu87"
LABEL version="3.2.0"
LABEL description="Self-hosted Spotify downloader"

LABEL org.opencontainers.image.title="Hify" \
      org.opencontainers.image.description="Download your Spotify playlists and songs along with album art and metadata in a self-hosted way via Docker" \
      org.opencontainers.image.version="3.2.0" \
      org.opencontainers.image.authors="Henrique Sebastião <contato@henriquesebastiao.com>" \
      org.opencontainers.image.url="https://github.com/hisu87/hify" \
      org.opencontainers.image.source="https://github.com/hisu87/hify" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.documentation="https://github.com/hisu87/hify#readme" \
      org.opencontainers.image.vendor="Henrique Sebastião" \
      org.opencontainers.image.base.name="python:3.13-alpine"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_COLORS=0 \
    HIFY_LOG_LEVEL=info \
    HIFY_PORT=8000 \
    UID=1000 \
    GID=1000 \
    UMASK=022

WORKDIR /hify

RUN apk add --no-cache \
    ffmpeg \
    shadow \
    su-exec \
    tini

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY main.py entrypoint.sh ./
COPY hify ./hify
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN sed -i 's/\r$//g' entrypoint.sh && \
    chmod +x entrypoint.sh

ENV PATH="/home/hify/.local/bin:${PATH}"

VOLUME /downloads
VOLUME /data

EXPOSE ${HIFY_PORT}

ENTRYPOINT ["/sbin/tini", "-g", "--", "./entrypoint.sh"]

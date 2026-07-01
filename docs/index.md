---
icon: lucide/house
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

<img src="assets/logo.svg" class="hero__logo" alt="Hify logo">

<h1 style="display: none;"></h1>

<div class="hero__title">Hify</div>

<p class="hero__lead">
The music downloader you can host on your own box.<br>
Drop a Spotify link, get a tagged audio file. No account, no API key, no Premium.
</p>

<div class="hero__cta" markdown>

[Get started](getting-started/installation.md){ .md-button .md-button--primary }
[Source on GitHub](https://github.com/hisu87/hify){ .md-button }

</div>

<div class="hero__shields" markdown>

[![Release](https://img.shields.io/github/v/release/hisu87/hify?color=1AD05C&label=release)](https://github.com/hisu87/hify/releases)
[![Docker Pulls](https://img.shields.io/docker/pulls/hisu87/hify?color=1AD05C)](https://hub.docker.com/r/hisu87/hify)
[![License](https://img.shields.io/github/license/hisu87/hify?color=1AD05C)](https://github.com/hisu87/hify/blob/main/LICENSE)

</div>

</div>

<section class="home-section" markdown>

## How it actually works

Spotify's official API gates downloads behind a Premium subscription. Hify takes the side door instead — it reads the metadata Spotify already exposes on its public embed pages, asks YouTube Music for the closest matching audio, hands the file to `yt-dlp` and `ffmpeg`, and writes proper tags with `mutagen`. The whole pipeline lives in a single Docker container.

<div class="pipeline">
  <div class="pipeline__step"><strong>Spotify embed</strong><br><span>metadata</span></div>
  <div class="pipeline__arrow">→</div>
  <div class="pipeline__step"><strong>YouTube Music</strong><br><span>audio match</span></div>
  <div class="pipeline__arrow">→</div>
  <div class="pipeline__step"><strong>yt-dlp · ffmpeg · mutagen</strong><br><span>download &amp; tag</span></div>
</div>

</section>

<section class="home-section" markdown>

## What you can paste in

| | |
|---|---|
| Spotify track | `open.spotify.com/track/…` |
| Spotify album | `open.spotify.com/album/…` |
| Spotify playlist | `open.spotify.com/playlist/…` |
| YouTube / YT Music | `youtube.com/watch?v=…` |
| Free-text search | `Arctic Monkeys Do I Wanna Know` |

</section>

<section class="home-section" markdown>

## Highlights

<div class="mini-grid">

<a href="features/playlist-monitor/" class="mini-card">
  <span class="mini-card__icon">👁</span>
  <span class="mini-card__title">Playlist Monitor</span>
  <span class="mini-card__text">Watches a playlist and quietly downloads new tracks as they're added.</span>
</a>

<a href="features/download-settings/" class="mini-card">
  <span class="mini-card__icon">🎚</span>
  <span class="mini-card__title">Five formats</span>
  <span class="mini-card__text">MP3, FLAC, M4A, OGG and OPUS — at the bitrate of your choice.</span>
</a>

<a href="features/lyrics/" class="mini-card">
  <span class="mini-card__icon">📝</span>
  <span class="mini-card__title">Lyrics built-in</span>
  <span class="mini-card__text">Plain and time-synced lyrics fetched from lrclib and embedded in the file.</span>
</a>

<a href="features/player/" class="mini-card">
  <span class="mini-card__icon">🎧</span>
  <span class="mini-card__title">Web player</span>
  <span class="mini-card__text">Shuffle, repeat, volume and album art — straight from the browser.</span>
</a>

<a href="features/m3u-export/" class="mini-card">
  <span class="mini-card__icon">📃</span>
  <span class="mini-card__title">M3U export</span>
  <span class="mini-card__text">Standard EXTM3U files that Jellyfin, Navidrome and Plex pick up automatically.</span>
</a>

<a href="features/file-organization/" class="mini-card">
  <span class="mini-card__icon">📁</span>
  <span class="mini-card__title">Library layout</span>
  <span class="mini-card__text">Flat dump or per-artist folders — whichever your media server prefers.</span>
</a>

</div>

</section>

<section class="home-section" markdown>

## One command and you're done

```bash
docker run -d -p 8000:8000 --name hify \
  -v /path/to/music:/downloads \
  -v hify_data:/data \
  ghcr.io/hisu87/hify
```

Open [`localhost:8000`](http://localhost:8000), paste a link, hit download. Files land in `/path/to/music` with the tags already in place.

[Installation guide](getting-started/installation.md){ .md-button .md-button--primary }
[Docker Compose](getting-started/docker-compose.md){ .md-button }

</section>

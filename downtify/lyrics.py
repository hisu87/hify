"""Lyrics providers used to enrich downloaded audio files.

Currently only ``lrclib`` (https://lrclib.net) is implemented. The legacy
``genius``/``musixmatch``/``azlyrics`` identifiers from the spotdl-era UI
are accepted as no-ops so existing settings keep round-tripping cleanly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests
from loguru import logger

LRCLIB_BASE = 'https://lrclib.net/api'
_USER_AGENT = 'Downtify (https://github.com/henriquesebastiao/downtify)'

SUPPORTED_PROVIDERS = {'lrclib'}


@dataclass
class Lyrics:
    plain: Optional[str] = None
    synced: Optional[str] = None

    def has_any(self) -> bool:
        return bool(self.plain) or bool(self.synced)


def fetch(song: dict[str, Any], providers: list[str]) -> Optional[Lyrics]:
    """Try each provider in order; return the first successful match."""

    for name in providers:
        if name not in SUPPORTED_PROVIDERS:
            continue
        try:
            result = _PROVIDER_FNS[name](song)
        except Exception:
            logger.exception('Lyrics provider {!r} failed', name)
            continue
        if result and result.has_any():
            return result
    return None


def _fallback_search_lrclib(
    title: str, artist: str
) -> Optional[dict[str, Any]]:
    search_params = {
        'track_name': title,
        'artist_name': artist,
    }
    try:
        response = requests.get(
            f'{LRCLIB_BASE}/search',
            params=search_params,
            headers={'User-Agent': _USER_AGENT},
            timeout=10,
        )
        if response.status_code != 200:
            return None
        results = response.json()
        if not results or not isinstance(results, list):
            return None

        for result in results:
            if result.get('syncedLyrics'):
                return result
        return results[0]
    except (requests.RequestException, ValueError):
        logger.opt(exception=True).warning('lrclib search fallback failed')
        return None


def _fetch_lrclib(song: dict[str, Any]) -> Optional[Lyrics]:
    artists = song.get('artists') or []
    title = (song.get('name') or '').strip()
    if not title or not artists:
        return None

    params = {
        'track_name': title,
        'artist_name': artists[0],
    }
    album = (song.get('album_name') or '').strip()
    if album:
        params['album_name'] = album
    duration = song.get('duration') or 0
    if duration:
        params['duration'] = int(duration)

    try:
        response = requests.get(
            f'{LRCLIB_BASE}/get',
            params=params,
            headers={'User-Agent': _USER_AGENT},
            timeout=10,
        )
    except requests.RequestException:
        logger.opt(exception=True).warning('lrclib request failed')
        return None

    data = None
    if response.status_code == 200:
        try:
            data = response.json()
        except ValueError:
            pass

    # Fallback to search if the exact match fails
    if not data or response.status_code == 404:
        fallback_data = _fallback_search_lrclib(title, artists[0])
        if fallback_data:
            data = fallback_data

    if not data:
        return None

    plain = (data.get('plainLyrics') or '').strip() or None
    synced = (data.get('syncedLyrics') or '').strip() or None
    if not plain and not synced:
        return None
    return Lyrics(plain=plain, synced=synced)


_PROVIDER_FNS = {
    'lrclib': _fetch_lrclib,
}

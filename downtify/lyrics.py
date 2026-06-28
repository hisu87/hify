"""Lyrics resolution and normalization via a Multi-Provider Chain.

This module implements the NormalizedLyrics AST to support multiple synced lyrics
providers (TTML, YRC, LRC, etc.) and standardizes them for the Frontend and ID3 tags.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from loguru import logger

if os.path.exists('/data'):
    CACHE_DB_PATH = '/data/lyrics_cache.db'
else:
    CACHE_DB_PATH = './data/lyrics_cache.db'

import re

import httpx
import syncedlyrics

from downtify.lyrics_db import cache_lyrics, get_cached_lyrics
from downtify.smart_matching import is_metadata_match


@dataclass
class NormalizedToken:
    text: str
    start_time: float  # Absolute seconds
    end_time: float
    is_trailing_space: bool


@dataclass
class NormalizedLine:
    start_time: float
    end_time: float
    raw_text: str
    is_instrumental: bool
    agent_id: str
    lead: list[NormalizedToken]
    background: Optional[list[NormalizedToken]] = None


@dataclass
class NormalizedLyrics:
    track_id: str
    isrc: Optional[str]
    provider_name: str
    sync_level: str  # 'syllable', 'word', 'line', 'plain'
    lines: list[NormalizedLine]

    def to_sidecar_lrc(self) -> str:
        """Render to enhanced/kinetic LRC format for external players."""
        out = []
        for line in self.lines:
            if line.is_instrumental:
                continue
            mins = int(line.start_time // 60)
            secs = line.start_time % 60
            prefix = f'[{mins:02d}:{secs:05.2f}]'

            if self.sync_level in {'word', 'syllable'} and line.lead:
                line_str = ''
                for token in line.lead:
                    t_mins = int(token.start_time // 60)
                    t_secs = token.start_time % 60
                    line_str += f'<{t_mins:02d}:{t_secs:05.2f}>{token.text}'
                    if token.is_trailing_space:
                        line_str += ' '
                out.append(f'{prefix}{line_str}')
            else:
                out.append(f'{prefix}{line.raw_text}')
        return '\n'.join(out)

    def to_audio_tag_text(self) -> str:
        """Render to standard line-level or plain text for ID3 USLT tags.
        Strips all word-level `<mm:ss.xx>` timestamps to comply with ID3 standard.
        """
        if self.sync_level == 'plain':
            return '\n'.join(
                line.raw_text
                for line in self.lines
                if not line.is_instrumental
            )

        out = []
        for line in self.lines:
            if line.is_instrumental:
                continue
            mins = int(line.start_time // 60)
            secs = line.start_time % 60
            prefix = f'[{mins:02d}:{secs:05.2f}]'
            out.append(f'{prefix}{line.raw_text}')
        return '\n'.join(out)

    # Backwards compatibility shim for existing ID3 embedding code
    @property
    def synced(self) -> Optional[str]:
        if self.sync_level == 'plain':
            return None
        return self.to_sidecar_lrc()

    @property
    def plain(self) -> Optional[str]:
        if self.sync_level == 'plain':
            return self.to_audio_tag_text()
        return None

    def has_any(self) -> bool:
        return len(self.lines) > 0


def enforce_time_rules(tokens: list[NormalizedToken]) -> list[NormalizedToken]:
    # 1. Sort by start_time
    tokens.sort(key=lambda x: x.start_time)
    # 2. Anti-Zero Duration (duration < 0.05)
    for t in tokens:
        if t.end_time - t.start_time < 0.05:
            t.end_time = t.start_time + 0.05
    return tokens


def estimate_tokens(
    line_text: str, line_start: float, line_end: float
) -> list[NormalizedToken]:
    tokens = []
    duration = line_end - line_start
    if duration < 0:
        duration = 0.05
    words = line_text.split(' ')
    total_chars = sum(len(w) for w in words)

    current_start = line_start
    for i, word in enumerate(words):
        if total_chars == 0:
            word_duration = duration / len(words) if words else duration
        else:
            word_duration = duration * (len(word) / total_chars)

        word_duration = max(word_duration, 0.05)

        word_end = current_start + word_duration
        is_trailing = i < len(words) - 1
        tokens.append(
            NormalizedToken(
                text=word,
                start_time=current_start,
                end_time=word_end,
                is_trailing_space=is_trailing,
            )
        )
        current_start = word_end

    return enforce_time_rules(tokens)


LRC_LINE_RE = re.compile(r'^\[(\d+):(\d+\.\d+|\d+)\](.*)$')
LRC_WORD_RE = re.compile(r'<(\d+):(\d+\.\d+|\d+)>([^<]*)')


def parse_enhanced_lrc(lrc_str: str) -> list[NormalizedLine]:
    lines = []
    for line in lrc_str.split('\n'):
        line = line.strip()
        if not line:
            continue
        line_match = LRC_LINE_RE.match(line)
        if not line_match:
            continue

        mins, secs, content = line_match.groups()
        line_start = int(mins) * 60 + float(secs)

        words = []
        word_matches = list(LRC_WORD_RE.finditer(content))
        if word_matches:
            for i, match in enumerate(word_matches):
                wmins, wsecs, wtext = match.groups()
                word_start = int(wmins) * 60 + float(wsecs)
                word_end = word_start
                if i < len(word_matches) - 1:
                    next_mins, next_secs, _ = word_matches[i + 1].groups()
                    word_end = int(next_mins) * 60 + float(next_secs)
                else:
                    word_end = word_start + 1.0

                is_trailing = wtext.endswith(' ')
                wtext_clean = wtext.strip()
                if wtext_clean:
                    words.append(
                        NormalizedToken(
                            text=wtext_clean,
                            start_time=word_start,
                            end_time=word_end,
                            is_trailing_space=is_trailing,
                        )
                    )

            lines.append(
                NormalizedLine(
                    start_time=line_start,
                    end_time=words[-1].end_time if words else line_start + 2.0,
                    raw_text=re.sub(r'<[^>]+>', '', content).strip(),
                    is_instrumental=False,
                    agent_id='lead_vocal',
                    lead=enforce_time_rules(words),
                )
            )
        else:
            lines.append(
                NormalizedLine(
                    start_time=line_start,
                    end_time=line_start + 2.0,
                    raw_text=content.strip(),
                    is_instrumental=False,
                    agent_id='lead_vocal',
                    lead=[],
                )
            )

    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            line.end_time = lines[i + 1].start_time
        if not line.lead and line.raw_text:
            line.lead = estimate_tokens(
                line.raw_text, line.start_time, line.end_time
            )

    return lines


import xml.etree.ElementTree as ET


def parse_time(time_str: str) -> float:
    parts = time_str.split(':')
    total = 0.0
    for p in parts:
        total = total * 60 + float(p)
    return total


def parse_amll_ttml(xml_str: str) -> list[NormalizedLine]:
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    lines = []
    for p in root.iter('{http://www.w3.org/ns/ttml}p'):
        begin = p.get('begin')
        end = p.get('end')
        agent = p.get(
            '{http://www.w3.org/ns/ttml#metadata}agent', 'lead_vocal'
        )
        if not begin or not end:
            continue

        line_start = parse_time(begin)
        line_end = parse_time(end)

        words = []
        raw_text = ''
        for span in p.iter('{http://www.w3.org/ns/ttml}span'):
            s_begin = span.get('begin')
            s_end = span.get('end')
            text = span.text or ''
            if not s_begin or not s_end:
                continue

            is_trailing = text.endswith(' ')
            text_clean = text.strip()
            if text_clean:
                words.append(
                    NormalizedToken(
                        text=text_clean,
                        start_time=parse_time(s_begin),
                        end_time=parse_time(s_end),
                        is_trailing_space=is_trailing,
                    )
                )
            raw_text += text

        lines.append(
            NormalizedLine(
                start_time=line_start,
                end_time=line_end,
                raw_text=raw_text.strip(),
                is_instrumental=False,
                agent_id=agent,
                lead=enforce_time_rules(words),
            )
        )
    return lines


class LyricsProvider(Protocol):
    name: str

    async def fetch(self, track: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Fetch raw payload specifically for this provider."""
        ...

    def normalize(
        self, raw_payload: dict[str, Any], track: dict[str, Any]
    ) -> Optional[NormalizedLyrics]:
        """Convert raw payload to NormalizedLyrics AST."""
        ...


class LyricsResolver:
    def __init__(
        self, providers: list[LyricsProvider], timeout_s: float = 3.5
    ):
        self.providers = providers
        self.timeout_s = timeout_s
        self._loop_limiters: dict[int, asyncio.Semaphore] = {}

    def _get_limiter(self) -> asyncio.Semaphore:
        """Lazy-binding: Khởi tạo Semaphore gắn chặt vào Event Loop đang chạy"""
        loop_id = id(asyncio.get_running_loop())
        if loop_id not in self._loop_limiters:
            self._loop_limiters[loop_id] = asyncio.Semaphore(5)
        return self._loop_limiters[loop_id]

    async def resolve(
        self, track: dict[str, Any]
    ) -> Optional[NormalizedLyrics]:
        track_id = track.get('id')
        if track_id:
            cached = await get_cached_lyrics(track_id)
            if cached:
                if cached.get('status') == 'NOT_FOUND':
                    return None
                if cached.get('status') == 'OK':
                    lines = []
                    for ld in cached['lines']:
                        lines.append(
                            NormalizedLine(
                                start_time=ld['start_time'],
                                end_time=ld['end_time'],
                                raw_text=ld['text'],
                                is_instrumental=ld.get('is_instrumental', False),
                                agent_id=ld['agent_id'],
                                lead=[
                                    NormalizedToken(**t) for t in ld['lead']
                                ],
                            )
                        )
                    return NormalizedLyrics(
                        track_id=track_id,
                        isrc=cached['isrc'],
                        provider_name=cached['provider_name'],
                        sync_level=cached['sync_level'],
                        lines=lines,
                    )

        limiter = self._get_limiter()
        in_memory_lrclib_fallback: Optional[dict[str, Any]] = None
        has_network_error = False

        async def evaluate_and_cache(
            provider, raw_payload
        ) -> Optional[NormalizedLyrics]:
            if not raw_payload or raw_payload.get('status') == 'NOT_FOUND':
                return None

            # Smart Matching check
            cand_meta = {}
            if provider.name == 'lrclib':
                cand_meta = {
                    'title': raw_payload.get('trackName', ''),
                    'artist': raw_payload.get('artistName', ''),
                    'duration_ms': raw_payload.get('duration', 0) * 1000
                    if raw_payload.get('duration')
                    else 0,
                }
            elif provider.name in ('netease', 'musixmatch'):
                lrc_str = raw_payload.get('lrc', '')
                ti_match = re.search(r'\[ti:(.*?)\]', lrc_str)
                ar_match = re.search(r'\[ar:(.*?)\]', lrc_str)
                length_match = re.search(r'\[length:(.*?)\]', lrc_str)
                cand_meta['title'] = ti_match.group(1) if ti_match else ''
                cand_meta['artist'] = ar_match.group(1) if ar_match else ''
                if length_match:
                    parts = length_match.group(1).split(':')
                    if len(parts) == 2:
                        try:
                            cand_meta['duration_ms'] = int(
                                (int(parts[0]) * 60 + float(parts[1])) * 1000
                            )
                        except Exception:
                            cand_meta['duration_ms'] = 0
                else:
                    cand_meta['duration_ms'] = 0

            if cand_meta.get('title') or cand_meta.get('artist'):
                if not is_metadata_match(track, cand_meta):
                    logger.debug(
                        f'{provider.name} rejected by Smart Matching: Track({track.get("title") or track.get("name")}) vs Cand({cand_meta.get("title")})'
                    )
                    return None

            result = provider.normalize(raw_payload, track)
            if result and result.has_any():
                if track_id:
                    # serialize for cache
                    payload = {
                        'status': 'OK',
                        'isrc': result.isrc,
                        'provider_name': result.provider_name,
                        'sync_level': result.sync_level,
                        'lines': result.lines,
                    }
                    await cache_lyrics(track_id, payload)
                return result
            return None

        # ── BƯỚC 1: Opportunistic LRCLIB ──
        lrclib_provider = next(
            (p for p in self.providers if p.name == 'lrclib'), None
        )
        if lrclib_provider:
            try:
                async with limiter:
                    raw_lrc = await asyncio.wait_for(
                        lrclib_provider.fetch(track), timeout=self.timeout_s
                    )
                if raw_lrc and raw_lrc.get('status') != 'NOT_FOUND':
                    in_memory_lrclib_fallback = raw_lrc
                    if not track.get('isrc') and raw_lrc.get('isrc'):
                        track['isrc'] = raw_lrc['isrc']
            except Exception as e:
                logger.debug(f'Opportunistic LRCLIB probe error: {e}')
                has_network_error = True

        # ── BƯỚC 2: Quét các Provider giàu Kinetic (AMLL -> NetEase) ──
        kinetic_providers = [
            p for p in self.providers if p.name not in {'lrclib', 'musixmatch'}
        ]
        for provider in kinetic_providers:
            try:
                async with limiter:
                    raw_payload = await asyncio.wait_for(
                        provider.fetch(track), timeout=self.timeout_s
                    )
                result = await evaluate_and_cache(provider, raw_payload)
                if result:
                    return result
            except Exception as e:
                logger.debug(f'Provider {provider.name} error: {e}')
                has_network_error = True
                continue

        # ── BƯỚC 3: Kích hoạt bí kíp LRCLIB ──
        if in_memory_lrclib_fallback and lrclib_provider:
            result = await evaluate_and_cache(
                lrclib_provider, in_memory_lrclib_fallback
            )
            if result:
                return result

        # ── BƯỚC 4: Chốt chặn cuối cùng (Musixmatch) ──
        mm_provider = next(
            (p for p in self.providers if p.name == 'musixmatch'), None
        )
        if mm_provider:
            try:
                async with limiter:
                    raw_mm = await asyncio.wait_for(
                        mm_provider.fetch(track), timeout=self.timeout_s
                    )
                result = await evaluate_and_cache(mm_provider, raw_mm)
                if result:
                    return result
            except Exception as e:
                logger.debug(f'Musixmatch error: {e}')
                has_network_error = True

        # No provider succeeded. Cache NOT_FOUND only if no network errors occurred.
        if not has_network_error and track_id:
            await cache_lyrics(track_id, {'status': 'NOT_FOUND'})

        return None


class AmllTtmlProvider(LyricsProvider):
    name = 'amll'

    async def fetch(self, track: dict[str, Any]) -> Optional[dict[str, Any]]:  # noqa: PLR6301
        isrc = track.get('isrc')
        if not isrc:
            return None
        url = f'https://raw.githubusercontent.com/amll-dev/amll-ttml-db/main/{isrc}.ttml'

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=3.0)
                if resp.status_code == 200:
                    return {'xml': resp.text}
                elif resp.status_code == 404:
                    return {'status': 'NOT_FOUND'}
        except Exception as e:
            logger.debug(f'AMLL fetch failed: {e}')
            raise
        return None

    def normalize(
        self, raw_payload: dict[str, Any], track: dict[str, Any]
    ) -> Optional[NormalizedLyrics]:
        if 'xml' not in raw_payload:
            return None
        lines = parse_amll_ttml(raw_payload['xml'])
        if not lines:
            return None
        return NormalizedLyrics(
            track_id=track.get('id', ''),
            isrc=track.get('isrc'),
            provider_name=self.name,
            sync_level='word'
            if any(line_obj.lead for line_obj in lines)
            else 'line',
            lines=lines,
        )


class NetEaseYrcProvider(LyricsProvider):
    name = 'netease'

    async def fetch(self, track: dict[str, Any]) -> Optional[dict[str, Any]]:  # noqa: PLR6301
        # 'title' is used by the lyrics search endpoint; Spotify-sourced
        # track dicts from spotify._track_dict() use 'name' instead.
        # Fall back to 'name' so both pipelines work correctly.
        title = track.get('title') or track.get('name', '')
        artist = track.get('subtitle', track.get('artist', ''))
        term = f'{title} {artist}'.strip()
        if not term:
            return None
        try:
            # Quân lệnh 1: Bọc Thread Pool cho I/O đồng bộ của syncedlyrics
            lrc_str = await asyncio.to_thread(
                syncedlyrics.search, term, providers=['NetEase']
            )
            if lrc_str:
                return {'lrc': lrc_str}
            return {'status': 'NOT_FOUND'}
        except Exception as e:
            logger.debug(f'NetEase fetch failed: {e}')
            raise
        return None

    def normalize(
        self, raw_payload: dict[str, Any], track: dict[str, Any]
    ) -> Optional[NormalizedLyrics]:
        if 'lrc' not in raw_payload:
            return None
        lines = parse_enhanced_lrc(raw_payload['lrc'])
        if not lines:
            return None
        return NormalizedLyrics(
            track_id=track.get('id', ''),
            isrc=track.get('isrc'),
            provider_name=self.name,
            sync_level='word'
            if any(line_obj.lead for line_obj in lines)
            else 'line',
            lines=lines,
        )


class MusixmatchTokenProvider(LyricsProvider):
    name = 'musixmatch'

    async def fetch(self, track: dict[str, Any]) -> Optional[dict[str, Any]]:  # noqa: PLR6301
        # Same 'title' vs 'name' key-mismatch fix as NetEaseYrcProvider.
        title = track.get('title') or track.get('name', '')
        artist = track.get('subtitle', track.get('artist', ''))
        term = f'{title} {artist}'.strip()
        if not term:
            return None
        try:
            lrc_str = await asyncio.to_thread(
                syncedlyrics.search, term, providers=['Musixmatch']
            )
            if lrc_str:
                return {'lrc': lrc_str}
            return {'status': 'NOT_FOUND'}
        except Exception as e:
            logger.debug(f'Musixmatch fetch failed: {e}')
            raise
        return None

    def normalize(
        self, raw_payload: dict[str, Any], track: dict[str, Any]
    ) -> Optional[NormalizedLyrics]:
        if 'lrc' not in raw_payload:
            return None
        lines = parse_enhanced_lrc(raw_payload['lrc'])
        if not lines:
            return None
        return NormalizedLyrics(
            track_id=track.get('id', ''),
            isrc=track.get('isrc'),
            provider_name=self.name,
            sync_level='word'
            if any(line_obj.lead for line_obj in lines)
            else 'line',
            lines=lines,
        )


class LrcLibProvider(LyricsProvider):
    name = 'lrclib'

    async def fetch(self, track: dict[str, Any]) -> Optional[dict[str, Any]]:  # noqa: PLR6301
        # Same 'title' vs 'name' key-mismatch fix; lrclib returns 400
        # Bad Request when track_name is empty.
        title = track.get('title') or track.get('name', '')
        artist = track.get('subtitle', track.get('artist', ''))
        album = track.get('album', '')
        duration = track.get('duration_ms', 0) / 1000.0

        url_get = 'https://lrclib.net/api/get'
        params = {
            'track_name': title,
            'artist_name': artist,
            'album_name': album,
            'duration': duration,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url_get, params=params, timeout=3.0)
                if resp.status_code == 200:
                    return resp.json()

                # Fallback to search
                url_search = 'https://lrclib.net/api/search'
                resp = await client.get(
                    url_search, params={'q': f'{title} {artist}'}, timeout=3.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
                return {'status': 'NOT_FOUND'}
        except Exception as e:
            logger.debug(f'LRCLIB fetch failed: {e}')
            raise
        return None

    def normalize(
        self, raw_payload: dict[str, Any], track: dict[str, Any]
    ) -> Optional[NormalizedLyrics]:
        # Quân lệnh 4: Xử lý cả line-level và word-level
        synced = raw_payload.get('syncedLyrics')
        plain = raw_payload.get('plainLyrics')

        lines = []
        if synced:
            lines = parse_enhanced_lrc(synced)
        elif plain:
            # Plain lyrics don't have time tags. So we can't estimate words without line boundaries.
            # LRCLIB usually returns plainLyrics alongside syncedLyrics.
            pass

        if not lines:
            return None
        return NormalizedLyrics(
            track_id=track.get('id', ''),
            isrc=track.get('isrc'),
            provider_name=self.name,
            sync_level='word'
            if any(line_obj.lead for line_obj in lines)
            else 'line',
            lines=lines,
        )


def resolve_sync(
    track: dict[str, Any], providers: list[str]
) -> Optional[NormalizedLyrics]:
    """Helper for downloader.py executor threads to safely run the async resolver."""
    loop = asyncio.new_event_loop()
    try:
        # Resolve providers
        provider_instances = []
        for p in providers:
            if p == 'amll':
                provider_instances.append(AmllTtmlProvider())
            elif p == 'netease':
                provider_instances.append(NetEaseYrcProvider())
            elif p == 'lrclib':
                provider_instances.append(LrcLibProvider())
            elif p == 'musixmatch':
                provider_instances.append(MusixmatchTokenProvider())

        resolver = LyricsResolver(providers=provider_instances)
        return loop.run_until_complete(resolver.resolve(track))
    finally:
        loop.close()


# Compatibility shim so downloader.py doesn't crash during incremental refactoring
def fetch(
    song: dict[str, Any], providers: list[str]
) -> Optional[NormalizedLyrics]:
    return resolve_sync(song, providers)

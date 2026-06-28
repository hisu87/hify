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

# [Paradox 3 Fix] Graceful fallback for local dev vs Docker
if os.path.exists('/data'):
    CACHE_DB_PATH = '/data/lyrics_cache.db'
else:
    CACHE_DB_PATH = './.cache/lyrics_cache.db'


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
        limiter = self._get_limiter()
        in_memory_lrclib_fallback: Optional[dict[str, Any]] = None

        # ── BƯỚC 1: Opportunistic LRCLIB (Tìm ISRC + Nhặt bí kíp dự phòng) ──
        lrclib_provider = next(
            (p for p in self.providers if p.name == 'lrclib'), None
        )
        if lrclib_provider:
            try:
                async with limiter:
                    raw_lrc = await asyncio.wait_for(
                        lrclib_provider.fetch(track), timeout=self.timeout_s
                    )
                if raw_lrc:
                    in_memory_lrclib_fallback = raw_lrc
                    # Bổ sung ISRC vào metadata nếu Spotify ban nãy chưa có
                    if not track.get('isrc') and raw_lrc.get('isrc'):
                        track['isrc'] = raw_lrc['isrc']
                        logger.debug(
                            f'Opportunistic ISRC enriched: {track["isrc"]}'
                        )
            except Exception as e:
                logger.debug(f'Opportunistic LRCLIB probe skipped: {e}')

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
                if raw_payload:
                    return provider.normalize(raw_payload, track)
            except Exception as e:
                logger.debug(f'Provider {provider.name} missed: {e}')
                continue

        # ── BƯỚC 3: Kích hoạt bí kíp LRCLIB đã nhặt ở Bước 1 (Zero HTTP Call) ──
        if in_memory_lrclib_fallback and lrclib_provider:
            logger.debug('Activating in-memory LRCLIB fallback cache...')
            return lrclib_provider.normalize(in_memory_lrclib_fallback, track)

        # ── BƯỚC 4: Chốt chặn cuối cùng (Musixmatch Anonymous Token) ──
        mm_provider = next(
            (p for p in self.providers if p.name == 'musixmatch'), None
        )
        if mm_provider:
            try:
                async with limiter:
                    raw_mm = await asyncio.wait_for(
                        mm_provider.fetch(track), timeout=self.timeout_s
                    )
                if raw_mm:
                    return mm_provider.normalize(raw_mm, track)
            except Exception as e:
                logger.debug(f'Musixmatch missed: {e}')

        return None


def resolve_sync(
    track: dict[str, Any], providers: list[str]
) -> Optional[NormalizedLyrics]:
    """Helper for downloader.py executor threads to safely run the async resolver."""
    loop = asyncio.new_event_loop()
    try:
        # TODO: Instantiate actual providers in Phase 2
        resolver = LyricsResolver(providers=[])
        return loop.run_until_complete(resolver.resolve(track))
    finally:
        loop.close()


# Compatibility shim so downloader.py doesn't crash during incremental refactoring
def fetch(
    song: dict[str, Any], providers: list[str]
) -> Optional[NormalizedLyrics]:
    return resolve_sync(song, providers)

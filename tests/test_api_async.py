"""Concurrency benchmarks proving async endpoints do not block the event loop."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from hify import api


@pytest.mark.asyncio
async def test_download_url_endpoint_does_not_block_event_loop(monkeypatch):
    app = FastAPI()
    app.include_router(api.router)

    # Mock state dependencies
    mock_downloader = MagicMock()
    mock_downloader.existing_filename_for.return_value = (
        'already_downloaded.mp3'
    )
    monkeypatch.setattr(api.state, 'downloader', mock_downloader)

    # Simulate slow synchronous network I/O (e.g. 0.5s Spotify scrape)
    def fake_slow_song_lookup(url: str):
        time.sleep(0.5)
        return {
            'song_id': 'slow123',
            'name': 'Slow Track',
            'artists': ['Artist'],
            'duration': 180,
        }

    monkeypatch.setattr(api, '_song_for_download', fake_slow_song_lookup)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as client:
        t0 = time.perf_counter()

        # Execute slow download resolution AND fast version check concurrently
        slow_task = asyncio.create_task(
            client.post('/api/download/url?url=https://spotify.com/track/123')
        )

        # Give the slow task 0.05s to start executing in its thread
        await asyncio.sleep(0.05)

        fast_res = await client.get('/api/version')
        fast_elapsed = time.perf_counter() - t0

        await slow_task

        assert fast_res.status_code == 200
        # If the loop was blocked by time.sleep(0.5), fast_elapsed would be >= 0.5s
        print(
            f'\n[Benchmark] Fast endpoint resolved during slow blocking task in {fast_elapsed:.4f}s'
        )
        assert fast_elapsed < 0.2


if __name__ == '__main__':
    pytest.main(['-s', '-v', __file__])

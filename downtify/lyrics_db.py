import json
import os
import time
from typing import Optional

import aiosqlite
from loguru import logger

DB_PATH = os.environ.get('DOWNTIFY_DATA_DIR', './data') + '/lyrics_cache.db'


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('PRAGMA journal_mode=WAL;')
        await db.execute('PRAGMA synchronous=NORMAL;')
        await db.execute('PRAGMA busy_timeout=5000;')

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tracks_lyrics (
                id TEXT PRIMARY KEY,
                isrc TEXT,
                provider TEXT,
                status TEXT NOT NULL,
                sync_level TEXT,
                lines_json TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
        """)
        await db.commit()


async def get_cached_lyrics(track_id: str) -> Optional[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                'SELECT isrc, provider, status, sync_level, lines_json, updated_at FROM tracks_lyrics WHERE id = ?',
                (track_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                isrc, provider, status, sync_level, lines_json, updated_at = (
                    row
                )

                # Check TTL for NOT_FOUND (7 days = 604800 seconds)
                if status == 'NOT_FOUND':
                    if time.time() - updated_at > 604800:
                        return None  # expired
                    return {'status': 'NOT_FOUND'}

                if status == 'OK':
                    return {
                        'status': 'OK',
                        'isrc': isrc,
                        'provider_name': provider,
                        'sync_level': sync_level,
                        'lines': json.loads(lines_json) if lines_json else [],
                    }
                return None
    except Exception as e:
        logger.error(f'DB Error getting cache for {track_id}: {e}')
        return None


async def cache_lyrics(track_id: str, payload: dict):
    # payload is the output of resolver OR {"status": "NOT_FOUND"}
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            now = int(time.time())

            if payload.get('status') == 'NOT_FOUND':
                await db.execute(
                    """
                    INSERT INTO tracks_lyrics (id, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET 
                        status=excluded.status, 
                        updated_at=excluded.updated_at
                """,
                    (track_id, 'NOT_FOUND', now, now),
                )
            else:
                lines = payload.get('lines', [])
                if not lines:
                    return  # DO NOT CACHE OK if no lines (Cache Poisoning Protection)

                from downtify.lyrics import NormalizedLine

                lines_list = []
                for line in lines:
                    if isinstance(line, NormalizedLine):
                        l_dict = {
                            'start_time': line.start_time,
                            'end_time': line.end_time,
                            'duration': line.duration,
                            'text': line.text,
                            'agent_id': line.agent_id,
                            'lead': [
                                {
                                    'start_time': t.start_time,
                                    'end_time': t.end_time,
                                    'duration': t.duration,
                                    'text': t.text,
                                }
                                for t in line.lead
                            ]
                            if line.lead
                            else [],
                            'bg': [
                                {
                                    'start_time': t.start_time,
                                    'end_time': t.end_time,
                                    'duration': t.duration,
                                    'text': t.text,
                                }
                                for t in line.bg
                            ]
                            if line.bg
                            else [],
                        }
                        lines_list.append(l_dict)
                    else:
                        lines_list.append(line)

                lines_json = json.dumps(lines_list)

                await db.execute(
                    """
                    INSERT INTO tracks_lyrics (id, isrc, provider, status, sync_level, lines_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET 
                        isrc=excluded.isrc,
                        provider=excluded.provider,
                        status=excluded.status, 
                        sync_level=excluded.sync_level,
                        lines_json=excluded.lines_json,
                        updated_at=excluded.updated_at
                """,
                    (
                        track_id,
                        payload.get('isrc'),
                        payload.get('provider_name'),
                        'OK',
                        payload.get('sync_level'),
                        lines_json,
                        now,
                        now,
                    ),
                )
            await db.commit()
    except Exception as e:
        logger.error(f'DB Error caching lyrics for {track_id}: {e}')

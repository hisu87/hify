import datetime
import json
import os
from typing import Optional

import aiosqlite
from loguru import logger

DB_PATH = os.environ.get('HIFY_DATA_DIR', '/data') + '/hify.db'


async def init_db():
    # Schema is now initialized by DatabaseManager in main.py, but we ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('PRAGMA foreign_keys = ON;')
        await db.execute('PRAGMA journal_mode=WAL;')
        await db.execute('PRAGMA synchronous=NORMAL;')
        await db.execute('PRAGMA busy_timeout=5000;')


async def get_cached_lyrics(track_id: str) -> Optional[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                'SELECT format_type, parsed_word_json, updated_at FROM lyrics_store WHERE track_id = ?',
                (track_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                format_type, parsed_word_json, updated_at = row

                # Check for cache expiration (30 days)
                if updated_at:
                    try:
                        # Assuming updated_at is stored in ISO format or similar timestamp by CURRENT_TIMESTAMP
                        dt = (
                            datetime.datetime.fromisoformat(
                                updated_at.replace('Z', '+00:00')
                            )
                            if 'T' in updated_at
                            else datetime.datetime.strptime(
                                updated_at, '%Y-%m-%d %H:%M:%S'
                            )
                        )
                        if (datetime.datetime.now() - dt).days > 30:
                            return None
                    except Exception as e:
                        logger.error(
                            f'Error parsing updated_at for cache invalidation: {e}'
                        )

                # Check for NOT_FOUND
                if format_type == 'NOT_FOUND':
                    return {'status': 'NOT_FOUND'}

                return {
                    'status': 'OK',
                    'sync_level': 'word' if format_type == 'TTML' else 'line',
                    'lines': json.loads(parsed_word_json)
                    if parsed_word_json
                    else [],
                }
    except Exception as e:
        logger.error(f'DB Error getting cache for {track_id}: {e}')
        return None


async def cache_lyrics(track_id: str, payload: dict):
    # payload is the output of resolver OR {"status": "NOT_FOUND"}
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('PRAGMA foreign_keys = ON;')

            # Ensure the track exists in the tracks table to satisfy FOREIGN KEY constraint
            await db.execute(
                'INSERT OR IGNORE INTO tracks (id, title) VALUES (?, ?)',
                (track_id, 'Unknown Title'),
            )

            if payload.get('status') == 'NOT_FOUND':
                await db.execute(
                    """
                    INSERT INTO lyrics_store (track_id, format_type)
                    VALUES (?, ?)
                    ON CONFLICT(track_id) DO UPDATE SET
                        format_type=excluded.format_type,
                        updated_at=CURRENT_TIMESTAMP
                """,
                    (track_id, 'NOT_FOUND'),
                )
            else:
                lines = payload.get('lines', [])
                if not lines:
                    return

                from hify.lyrics import NormalizedLine

                lines_list = []
                for line in lines:
                    if isinstance(line, NormalizedLine):
                        l_dict = {
                            'start_time': line.start_time,
                            'end_time': line.end_time,
                            'text': line.raw_text,
                            'is_instrumental': line.is_instrumental,
                            'agent_id': line.agent_id,
                            'lead': [
                                {
                                    'start_time': t.start_time,
                                    'end_time': t.end_time,
                                    'text': t.text,
                                    'is_trailing_space': t.is_trailing_space,
                                }
                                for t in line.lead
                            ]
                            if line.lead
                            else [],
                        }
                        lines_list.append(l_dict)
                    else:
                        lines_list.append(line)

                parsed_word_json = json.dumps(lines_list)
                sync_level = payload.get('sync_level', 'line')
                format_type = 'TTML' if sync_level == 'word' else 'LRC'

                await db.execute(
                    """
                    INSERT INTO lyrics_store (track_id, format_type, parsed_word_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(track_id) DO UPDATE SET
                        format_type=excluded.format_type,
                        parsed_word_json=excluded.parsed_word_json,
                        updated_at=CURRENT_TIMESTAMP
                """,
                    (
                        track_id,
                        format_type,
                        parsed_word_json,
                    ),
                )
            await db.commit()
    except Exception as e:
        logger.error(f'DB Error caching lyrics for {track_id}: {e}')

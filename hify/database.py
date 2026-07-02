import os
import sqlite3
from pathlib import Path
from typing import List, Optional

from loguru import logger


class DatabaseManager:
    def __init__(self, db_path: Path):
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS artists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    spotify_id TEXT UNIQUE,
                    thumbnail TEXT
                );

                CREATE TABLE IF NOT EXISTS albums (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    spotify_id TEXT UNIQUE,
                    cover_art_path TEXT,
                    release_year TEXT
                );

                CREATE TABLE IF NOT EXISTS genres (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tracks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    file_path TEXT UNIQUE,
                    file_hash TEXT,
                    duration INTEGER,
                    artist_id TEXT,
                    album_id TEXT,
                    genre_id TEXT,
                    lyrics_path TEXT,
                    FOREIGN KEY(artist_id) REFERENCES artists(id) ON DELETE SET NULL,
                    FOREIGN KEY(album_id) REFERENCES albums(id) ON DELETE SET NULL,
                    FOREIGN KEY(genre_id) REFERENCES genres(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS lyrics_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT NOT NULL UNIQUE,
                    format_type TEXT, -- 'TTML' or 'LRC' or 'JSON'
                    raw_content TEXT,
                    parsed_word_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
                );

                -- Add updated_at column to existing lyrics_store if it doesn't exist
                -- We wrap it in a try block using Python logic below, or we can use PRAGMA table_info to check
                -- But SQLite ALTER TABLE ADD COLUMN IF NOT EXISTS is only available in 3.25+. We can add a migration step below.

                CREATE INDEX IF NOT EXISTS idx_tracks_file_hash ON tracks(file_hash);
                CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
                CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name);
                CREATE INDEX IF NOT EXISTS idx_lyrics_store_track_id ON lyrics_store(track_id);
            """)

            # Migration for updated_at
            try:
                # Add updated_at if not exists
                cursor = conn.execute('PRAGMA table_info(lyrics_store)')
                columns = [info[1] for info in cursor.fetchall()]
                if 'updated_at' not in columns:
                    conn.execute(
                        'ALTER TABLE lyrics_store ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                    )
            except Exception as e:
                logger.error(f'Migration error: {e}')

    def get_track_metadata(self, track_id: str) -> Optional[dict]:
        with self._connect() as conn:
            query = """
                SELECT t.id, t.title, t.file_path, t.duration,
                       ar.name as artist, ar.thumbnail as artist_thumb,
                       al.title as album, al.cover_art_path as cover_url, al.release_year as year,
                       g.name as genre
                FROM tracks t
                LEFT JOIN artists ar ON t.artist_id = ar.id
                LEFT JOIN albums al ON t.album_id = al.id
                LEFT JOIN genres g ON t.genre_id = g.id
                WHERE t.id = ?
            """
            row = conn.execute(query, (track_id,)).fetchone()
            if row:
                return dict(row)
            return None

    def list_all_tracks(self) -> List[dict]:
        with self._connect() as conn:
            query = """
                SELECT t.id, t.title, t.file_path as file, t.duration as duration_ms,
                       ar.name as artist, ar.thumbnail as artist_thumb,
                       al.title as album, al.cover_art_path as cover_url, al.release_year as year,
                       g.name as genre
                FROM tracks t
                LEFT JOIN artists ar ON t.artist_id = ar.id
                LEFT JOIN albums al ON t.album_id = al.id
                LEFT JOIN genres g ON t.genre_id = g.id
                ORDER BY t.title ASC
            """
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def delete_orphan_tracks(self, valid_paths: set):
        with self._connect() as conn:
            try:
                rows = conn.execute(
                    'SELECT id, file_path FROM tracks'
                ).fetchall()
                deleted = 0
                for r in rows:
                    if r['file_path'] not in valid_paths:
                        conn.execute(
                            'DELETE FROM tracks WHERE id = ?', (r['id'],)
                        )
                        deleted += 1
                conn.commit()
                if deleted > 0:
                    logger.info(
                        f'Cleaned up {deleted} orphaned tracks from DB.'
                    )
            except Exception as e:
                logger.error(f'Error cleaning orphan tracks: {e}')

    def save_track_metadata(self, track_id: str, data: dict):
        with self._connect() as conn:
            try:
                # Basic upsert for artist
                artist_name = data.get('artist') or (
                    data.get('artists')[0] if data.get('artists') else ''
                )
                artist_id = f'ar_{hash(artist_name)}' if artist_name else None
                if artist_id and artist_name:
                    conn.execute(
                        'INSERT OR IGNORE INTO artists (id, name) VALUES (?, ?)',
                        (artist_id, artist_name),
                    )

                # Basic upsert for album
                album_name = data.get('album_name') or data.get('album')
                album_id = f'al_{hash(album_name)}' if album_name else None
                if album_id and album_name:
                    conn.execute(
                        'INSERT OR IGNORE INTO albums (id, title, cover_art_path, release_year) VALUES (?, ?, ?, ?)',
                        (
                            album_id,
                            album_name,
                            data.get('cover_url'),
                            data.get('year'),
                        ),
                    )

                # Basic upsert for genre
                genre_name = data.get('genre')
                genre_id = f'gn_{hash(genre_name)}' if genre_name else None
                if genre_id and genre_name:
                    conn.execute(
                        'INSERT OR IGNORE INTO genres (id, name) VALUES (?, ?)',
                        (genre_id, genre_name),
                    )

                # Track
                conn.execute(
                    """
                    INSERT INTO tracks (id, title, file_path, file_hash, duration, artist_id, album_id, genre_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    file_path=excluded.file_path,
                    file_hash=excluded.file_hash,
                    duration=excluded.duration,
                    artist_id=excluded.artist_id,
                    album_id=excluded.album_id,
                    genre_id=excluded.genre_id
                    """,
                    (
                        track_id,
                        data.get('title') or data.get('name') or 'Unknown',
                        data.get('file_path'),
                        data.get('file_hash'),
                        data.get('duration_ms') or data.get('duration'),
                        artist_id,
                        album_id,
                        genre_id,
                    ),
                )
                conn.commit()
            except Exception as e:
                logger.error(f'Error saving track metadata: {e}')


# Global instance initialization will be handled in main.py

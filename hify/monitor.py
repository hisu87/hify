"""Periodic playlist monitoring and automatic downloading."""

from __future__ import annotations

import asyncio
import hashlib
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger
from mutagen import File as MutagenFile

from . import m3u, spotify
from .downloader import Downloader

MONITOR_LOOP_INTERVAL = 60  # seconds between loop sweeps


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_due(last_checked: Optional[str], interval_minutes: int) -> bool:
    if last_checked is None:
        return True
    try:
        last = datetime.fromisoformat(last_checked)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= last + timedelta(
            minutes=interval_minutes
        )
    except ValueError:
        return True


@dataclass
class MonitoredPlaylist:
    id: int
    spotify_id: str
    name: str
    url: str
    interval_minutes: int
    enabled: bool
    last_checked: Optional[str]
    last_track_count: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_UPDATE_CLAUSES: dict[str, str] = {
    'interval_minutes': 'interval_minutes = ?',
    'enabled': 'enabled = ?',
    'last_checked': 'last_checked = ?',
    'last_track_count': 'last_track_count = ?',
    'name': 'name = ?',
}


class PlaylistMonitorDB:
    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = asyncio.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS monitored_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL DEFAULT 60,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_checked TEXT,
                    last_track_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS downloaded_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    track_spotify_id TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    FOREIGN KEY (playlist_id) REFERENCES monitored_playlists(id)
                        ON DELETE CASCADE,
                    UNIQUE(playlist_id, track_spotify_id)
                );
                CREATE INDEX IF NOT EXISTS idx_downloaded_track_spotify_id 
                    ON downloaded_tracks(track_spotify_id);
            """)
            # Migration: add filename column if it doesn't exist yet
            try:
                conn.execute(
                    'ALTER TABLE downloaded_tracks ADD COLUMN filename TEXT'
                )
            except Exception:
                pass

    def add_playlist(
        self,
        spotify_id: str,
        name: str,
        url: str,
        interval_minutes: int = 60,
    ) -> MonitoredPlaylist:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO monitored_playlists
                   (spotify_id, name, url, interval_minutes, enabled, created_at)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (spotify_id, name, url, interval_minutes, _now_iso()),
            )
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (cur.lastrowid,),
            ).fetchone()
            return _row_to_playlist(row)

    def list_playlists(self) -> list[MonitoredPlaylist]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM monitored_playlists ORDER BY created_at DESC'
            ).fetchall()
            return [_row_to_playlist(r) for r in rows]

    def get_playlist(self, playlist_id: int) -> Optional[MonitoredPlaylist]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def get_by_spotify_id(
        self, spotify_id: str
    ) -> Optional[MonitoredPlaylist]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE spotify_id = ?',
                (spotify_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def delete_playlist(self, playlist_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            )
            return cur.rowcount > 0

    def update_playlist(
        self, playlist_id: int, **kwargs: Any
    ) -> Optional[MonitoredPlaylist]:
        clauses: list[str] = []
        values: list[Any] = []

        # Iterate static clauses to guarantee zero user-key string interpolation
        for col, clause in _UPDATE_CLAUSES.items():
            if col in kwargs:
                clauses.append(clause)
                values.append(kwargs[col])

        if not clauses:
            return self.get_playlist(playlist_id)

        set_clause = ', '.join(clauses)
        values.append(playlist_id)
        with self._connect() as conn:
            conn.execute(
                f'UPDATE monitored_playlists SET {set_clause} WHERE id = ?',
                values,
            )
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def get_track_filenames(
        self, playlist_id: int
    ) -> dict[str, Optional[str]]:
        """Return ``{track_spotify_id: filename}`` for all known tracks."""
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT track_spotify_id, filename FROM downloaded_tracks WHERE playlist_id = ?',
                (playlist_id,),
            ).fetchall()
            return {r['track_spotify_id']: r['filename'] for r in rows}

    def mark_track_downloaded(
        self,
        playlist_id: int,
        track_spotify_id: str,
        filename: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO downloaded_tracks
                   (playlist_id, track_spotify_id, downloaded_at, filename)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(playlist_id, track_spotify_id) DO UPDATE SET
                   downloaded_at=excluded.downloaded_at,
                   filename=excluded.filename""",
                (playlist_id, track_spotify_id, _now_iso(), filename),
            )

    def mark_tracks_downloaded(
        self,
        playlist_id: int,
        tracks: list[tuple[str, str, Optional[str]]],
    ) -> None:
        """Batch insert ``[(track_spotify_id, downloaded_at, filename)]`` records."""
        if not tracks:
            return
        payload = [(playlist_id, tid, dt, fname) for tid, dt, fname in tracks]
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO downloaded_tracks
                   (playlist_id, track_spotify_id, downloaded_at, filename)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(playlist_id, track_spotify_id) DO UPDATE SET
                   downloaded_at=excluded.downloaded_at,
                   filename=excluded.filename""",
                payload,
            )


def _row_to_playlist(row: sqlite3.Row) -> MonitoredPlaylist:
    return MonitoredPlaylist(
        id=row['id'],
        spotify_id=row['spotify_id'],
        name=row['name'],
        url=row['url'],
        interval_minutes=row['interval_minutes'],
        enabled=bool(row['enabled']),
        last_checked=row['last_checked'],
        last_track_count=row['last_track_count'],
        created_at=row['created_at'],
    )


async def check_playlist(  # noqa: PLR0913
    playlist: MonitoredPlaylist,
    db: PlaylistMonitorDB,
    downloader: Downloader,
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
) -> int:
    """Fetch playlist, detect new tracks, download them. Returns count downloaded."""
    logger.info(
        'Checking monitored playlist "{}" ({})',
        playlist.name,
        playlist.spotify_id,
    )

    try:
        tracks = await asyncio.to_thread(
            spotify.playlist_tracks_from_id, playlist.spotify_id
        )
    except Exception:
        logger.exception('Failed to fetch playlist {}', playlist.spotify_id)
        await asyncio.to_thread(
            db.update_playlist, playlist.id, last_checked=_now_iso()
        )
        return 0

    known_tracks = await asyncio.to_thread(db.get_track_filenames, playlist.id)

    pl_subdir = m3u.sanitize_playlist_name(playlist.name)

    def _find_new_tracks() -> list[dict[str, Any]]:
        missing = []
        for t in tracks:
            if not t.get('song_id'):
                continue
            tid = t['song_id']
            if tid not in known_tracks:
                missing.append(t)
            else:
                stored = known_tracks[tid]
                if (
                    stored is not None
                    and not (downloader.download_dir / stored).exists()
                ):
                    # File was deleted — re-download
                    missing.append(t)
        return missing

    # ⚡ OPTIMIZATION: Offload O(N) disk I/O operations to a thread to
    # prevent blocking the asyncio main event loop on large playlists.
    new_tracks = await asyncio.to_thread(_find_new_tracks)

    if new_tracks:
        logger.info(
            'Found {} track(s) to download in playlist "{}"',
            len(new_tracks),
            playlist.name,
        )

    downloaded = 0
    batch_records: list[tuple[str, str, Optional[str]]] = []

    # Fetch all missing per-track metadata concurrently, with a limit to avoid rate limits
    semaphore = asyncio.Semaphore(10)

    async def _fetch_metadata(song: dict[str, Any]) -> None:
        track_id = song.get('song_id')
        if not track_id:
            return
        async with semaphore:
            try:
                full = await asyncio.to_thread(spotify.track_from_id, track_id)
                for key in (
                    'cover_url',
                    'year',
                    'release_date',
                    'album_name',
                    'artists',
                ):
                    value = full.get(key)
                    if value:
                        song[key] = value
            except Exception:
                logger.opt(exception=True).warning(
                    'Per-track Spotify fetch failed for {}; '
                    'falling back to playlist data',
                    track_id,
                )

    if new_tracks:
        await asyncio.gather(*(_fetch_metadata(s) for s in new_tracks))

    for song in new_tracks:
        track_id = song['song_id']
        pl_name = playlist.name

        def _make_cb(s: dict, name: str) -> Callable[[float, str], None]:
            def _cb(pct: float, message: str) -> None:
                asyncio.run_coroutine_threadsafe(
                    broadcast({
                        'song': s,
                        'progress': pct,
                        'message': message,
                        'playlist_name': name,
                    }),
                    loop,
                )

            return _cb

        try:
            filename = await loop.run_in_executor(
                None,
                lambda s=song: downloader.download(
                    s, _make_cb(s, pl_name), subdir=pl_subdir
                ),
            )
            batch_records.append((track_id, _now_iso(), filename))
            downloaded += 1

            # Step 2.5: Save to unified tracks metadata DB
            if hasattr(db, '_path'):
                try:
                    import sqlite3
                    # Use a quick sync connection since this runs rarely
                    with sqlite3.connect(db._path, check_same_thread=False) as conn:
                        artist_name = song.get('artist') or (song.get('artists')[0] if song.get('artists') else '')
                        artist_id = f"ar_{hash(artist_name)}" if artist_name else None
                        if artist_id and artist_name:
                            conn.execute("INSERT OR IGNORE INTO artists (id, name) VALUES (?, ?)", (artist_id, artist_name))

                        album_name = song.get('album_name') or song.get('album')
                        album_id = f"al_{hash(album_name)}" if album_name else None
                        if album_id and album_name:
                            conn.execute("INSERT OR IGNORE INTO albums (id, title, cover_art_path, release_year) VALUES (?, ?, ?, ?)",
                                        (album_id, album_name, song.get('cover_url'), song.get('year')))

                        conn.execute("""
                            INSERT INTO tracks (id, title, file_path, duration, artist_id, album_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                            title=excluded.title, file_path=excluded.file_path, duration=excluded.duration
                        """, (
                            track_id,
                            song.get('title') or song.get('name'),
                            filename,
                            song.get('duration_ms') or song.get('duration'),
                            artist_id,
                            album_id
                        ))
                except Exception as e:
                    logger.error(f"Error saving background track metadata: {e}")

            # Step 3: Background Task (Tải lyrics ngầm)
            async def _bg_fetch_lyrics(s_dict: dict[str, Any]):
                from hify import lyrics
                eff = settings.get('lyrics_providers', 'lrclib') if settings else 'lrclib'
                provs = []
                for p in [x.strip() for x in eff.split(',') if x.strip()]:
                    if p == 'amll': provs.append(lyrics.AmllTtmlProvider())
                    elif p == 'netease': provs.append(lyrics.NetEaseYrcProvider())
                    elif p == 'lrclib': provs.append(lyrics.LrcLibProvider())
                    elif p == 'musixmatch': provs.append(lyrics.MusixmatchTokenProvider())
                if not provs: provs.append(lyrics.LrcLibProvider())

                res = lyrics.LyricsResolver(providers=provs)
                try:
                    # Tự động cache vào lyrics_db bên trong hàm resolve
                    await res.resolve(s_dict)
                    logger.debug('Successfully cached background lyrics for {}', s_dict.get('song_id'))
                except Exception as e:
                    logger.warning('Failed background lyrics fetch for {}: {}', s_dict.get('song_id'), e)

            # Khởi chạy ngầm không chặn luồng chính
            asyncio.create_task(_bg_fetch_lyrics(song))

        except Exception:
            logger.exception('Failed to auto-download track {}', track_id)

    if batch_records:
        await asyncio.to_thread(
            db.mark_tracks_downloaded, playlist.id, batch_records
        )

    await asyncio.to_thread(
        db.update_playlist,
        playlist.id,
        last_checked=_now_iso(),
        last_track_count=len(tracks),
    )

    if downloaded > 0 and (
        settings is None or settings.get('generate_m3u', True)
    ):
        await asyncio.to_thread(_regenerate_m3u, playlist, tracks, downloader)
    return downloaded


def _regenerate_m3u(
    playlist: MonitoredPlaylist,
    tracks: list[dict[str, Any]],
    downloader: Downloader,
) -> None:
    """Rewrite the playlist's M3U from on-disk state after a sweep.

    Walks the full ordered track list (not just the freshly downloaded
    ones), resolves each to an existing file via the downloader, and
    hands the entries to :func:`m3u.write_m3u`. Tracks without a
    matching file on disk are dropped.
    """

    pl_subdir = m3u.sanitize_playlist_name(playlist.name)
    entries: list[dict[str, Any]] = []
    for song in tracks:
        filename = downloader.existing_filename_for(song, subdir=pl_subdir)
        if not filename:
            continue
        entries.append({
            'filename': filename,
            'title': song.get('name', ''),
            'artist': ', '.join(song.get('artists') or []),
            'duration': song.get('duration', 0),
        })
    if not entries:
        logger.warning(
            'M3U skip for monitored playlist "{}": no tracks on disk',
            playlist.name,
        )
        return
    m3u.write_m3u(
        downloader.download_dir,
        playlist.name,
        entries,
        playlist_subdir=pl_subdir,
    )


async def monitor_loop(
    db: PlaylistMonitorDB,
    get_downloader: Callable[[], Optional[Downloader]],
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
) -> None:
    """Background task: sweep all enabled playlists that are due for checking."""
    while True:
        try:
            playlists = await asyncio.to_thread(db.list_playlists)
            for pl in playlists:
                if not pl.enabled:
                    continue
                if not _is_due(pl.last_checked, pl.interval_minutes):
                    continue
                downloader = get_downloader()
                if downloader is None:
                    continue
                try:
                    count = await check_playlist(
                        pl, db, downloader, broadcast, loop, settings
                    )
                    if count > 0:
                        logger.info(
                            'Auto-downloaded {} new track(s) from "{}"',
                            count,
                            pl.name,
                        )
                except Exception:
                    logger.exception(
                        'Error while checking playlist "{}"', pl.name
                    )
        except Exception:
            logger.exception('Unexpected error in monitor loop')
        await asyncio.sleep(MONITOR_LOOP_INTERVAL)


def sync_filesystem_to_db(download_dir: Path, db_manager):
    """
    Scan DOWNLOAD_DIR for audio files, extract tags via mutagen, and upsert into the database.
    Also removes tracks from DB that no longer exist on disk.
    """
    logger.info("Starting filesystem to DB sync...")
    valid_paths = set()
    extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav', '.aac'}
    covers_dir = Path("data/covers")
    covers_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for root, _, files in os.walk(download_dir):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() not in extensions:
                continue

            try:
                rel_path = file_path.relative_to(download_dir).as_posix()
                valid_paths.add(rel_path)

                # We skip metadata extraction if file_hash logic or mtime logic is used,
                # but to be safe and simple, let's parse basic tags using MutagenFile
                audio = MutagenFile(file_path)
                if audio is None:
                    continue

                # Basic tagging mappings
                title = file_path.stem
                artist = "Unknown"
                album = "Unknown"
                genre = None
                year = None
                duration_ms = 0
                cover_url = None

                if hasattr(audio, 'info') and audio.info:
                    duration_ms = int(audio.info.length * 1000)

                # ID3/FLAC tag mapping (very simplified, usually mutagen provides dict-like access)
                if hasattr(audio, 'tags') and audio.tags:
                    tags = audio.tags
                    if 'title' in tags or 'TIT2' in tags:
                        title = tags.get('title', tags.get('TIT2', [title]))[0]
                    if 'artist' in tags or 'TPE1' in tags:
                        artist = tags.get('artist', tags.get('TPE1', [artist]))[0]
                    if 'album' in tags or 'TALB' in tags:
                        album = tags.get('album', tags.get('TALB', [album]))[0]
                    if 'genre' in tags or 'TCON' in tags:
                        genre = tags.get('genre', tags.get('TCON', [genre]))[0]
                    if 'date' in tags or 'TYER' in tags or 'TDRC' in tags:
                        year = tags.get('date', tags.get('TYER', tags.get('TDRC', [year])))[0]

                # Cover Art Extraction
                # Use the logic similar to main.py `_extract_cover` but directly from `audio.pictures` or ID3 APIC
                cover_data = None
                if getattr(audio, 'pictures', None):
                    cover_data = audio.pictures[0].data
                elif hasattr(audio, 'tags') and audio.tags:
                    for tag in audio.tags.values():
                        # Check for APIC frame (ID3)
                        if type(tag).__name__ == 'APIC':
                            cover_data = tag.data
                            break
                        # Check for MP4 Cover
                        if type(tag).__name__ == 'MP4Cover':
                            cover_data = bytes(tag)
                            break

                if cover_data:
                    cover_hash = hashlib.md5(cover_data).hexdigest()
                    cover_file = covers_dir / f"{cover_hash}.jpg"  # Simplified to .jpg
                    if not cover_file.exists():
                        cover_file.write_bytes(cover_data)
                    cover_url = cover_file.as_posix()

                # Check for string conversion of mutagen tags
                title = str(title) if title else "Unknown"
                artist = str(artist) if artist else "Unknown"
                album = str(album) if album else "Unknown"
                genre = str(genre) if genre else None
                year = str(year) if year else None

                # Generate unique track ID based on file path
                track_id = f"tr_{hashlib.md5(rel_path.encode()).hexdigest()}"

                track_data = {
                    'title': title,
                    'artist': artist,
                    'album_name': album,
                    'genre': genre,
                    'year': year,
                    'duration_ms': duration_ms,
                    'file_path': rel_path,
                    'file_hash': track_id,  # Using the MD5 hash of path as file_hash for now
                    'cover_url': cover_url,
                }

                db_manager.save_track_metadata(track_id, track_data)
                count += 1

            except Exception as e:
                logger.error(f"Error parsing file {file_path}: {e}")

    logger.info(f"Sync complete. Upserted {count} tracks.")
    db_manager.delete_orphan_tracks(valid_paths)

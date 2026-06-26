"""Security and unit tests for PlaylistMonitorDB."""

from __future__ import annotations

import pytest

from downtify.monitor import PlaylistMonitorDB


@pytest.fixture
def monitor_db(tmp_path):
    db_file = tmp_path / 'test_monitor.db'
    return PlaylistMonitorDB(db_file)


def test_update_playlist_valid_columns(monitor_db):
    pl = monitor_db.add_playlist(
        'spot123', 'My Playlist', 'https://spotify.com/123'
    )

    updated = monitor_db.update_playlist(
        pl.id,
        name='Renamed Playlist',
        interval_minutes=120,
        last_track_count=25,
    )

    assert updated is not None
    assert updated.name == 'Renamed Playlist'
    assert updated.interval_minutes == 120
    assert updated.last_track_count == 25


def test_update_playlist_ignores_malicious_sql_injection_keys(monitor_db):
    pl = monitor_db.add_playlist(
        'spot456', 'Safe Playlist', 'https://spotify.com/456'
    )

    # Attempt SQL injection via column name tampering
    malicious_kwargs = {
        'name': 'Hacked Name',
        'enabled = 0; DROP TABLE monitored_playlists; --': 'malicious_payload',
        'nonexistent_column': 'ignored_val',
    }

    updated = monitor_db.update_playlist(pl.id, **malicious_kwargs)

    assert updated is not None
    assert updated.name == 'Hacked Name'
    # Table must survive clean and uncorrupted
    assert len(monitor_db.list_playlists()) == 1


def test_update_playlist_empty_kwargs_returns_unmodified(monitor_db):
    pl = monitor_db.add_playlist(
        'spot789', 'Empty Test', 'https://spotify.com/789'
    )

    result = monitor_db.update_playlist(pl.id)
    assert result == pl

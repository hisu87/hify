"""Security unit and integration tests for main.py filesystem endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main
from main import _is_safe_path, build_app


@pytest.mark.parametrize(
    'malicious_path',
    [
        '../../../etc/passwd',
        '..\\..\\Windows\\win.ini',
        '/absolute/path/song.mp3',
        'C:\\absolute\\song.mp3',
        'folder/../secret.env',
        'track.mp3\x00.png',
    ],
)
def test_is_safe_path_rejects_traversal_and_escapes(malicious_path):
    assert _is_safe_path(malicious_path) is False


@pytest.mark.parametrize(
    'safe_path',
    [
        'song.mp3',
        'Arctic Monkeys - 505.flac',
        'subfolder/track.ogg',
        'artist/my..song.mp3',  # Legitimate double dots in track title
    ],
)
def test_is_safe_path_allows_legitimate_relative_files(safe_path):
    assert _is_safe_path(safe_path) is True


def test_endpoints_reject_traversal_payloads_via_http(tmp_path, monkeypatch):
    # Sandbox global host directories to temporary test paths
    d_dir = tmp_path / 'downloads'
    db_dir = tmp_path / 'data'
    d_dir.mkdir()
    db_dir.mkdir()
    (db_dir / 'settings.json').write_text(
        '{"format": "mp3", "output": "{title}.{output-ext}"}', encoding='utf-8'
    )

    monkeypatch.setattr(main, 'DOWNLOAD_DIR', d_dir)
    monkeypatch.setattr(main, 'DATABASE_DIR', db_dir)

    # Also sandbox WEB_GUI_LOCATION to avoid directory missing error
    gui_dir = tmp_path / 'gui'
    gui_dir.mkdir()
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(gui_dir))

    client = TestClient(build_app())

    # Verify GET /cover rejection
    res_cover = client.get('/cover', params={'file': '../../etc/passwd'})
    assert res_cover.status_code == 400
    assert 'traversal' in res_cover.json()['detail']

    # Verify DELETE /delete rejection
    res_del = client.delete('/delete', params={'file': '/root/secret.key'})
    assert res_del.status_code == 200
    assert res_del.json() == {
        'deleted': False,
        'error': 'Invalid path: traversal components not allowed',
    }

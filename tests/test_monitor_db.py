import time
from pathlib import Path

import pytest

from hify.monitor import PlaylistMonitorDB


@pytest.fixture
def monitor_db(tmp_path: Path):
    db_path = tmp_path / 'test_monitor.db'
    return PlaylistMonitorDB(db_path)


def test_mark_tracks_downloaded_batch_correctness(monitor_db):
    pl = monitor_db.add_playlist(
        'spot_batch', 'Batch PL', 'https://open.spotify.com/playlist/…0'
    )
    batch_data = [
        ('track_1', '2026-06-26T10:00:00+00:00', 'file1.mp3'),
        ('track_2', '2026-06-26T10:01:00+00:00', 'file2.mp3'),
    ]

    # We will implement this
    monitor_db.mark_tracks_downloaded(pl.id, batch_data)

    stored = monitor_db.get_track_filenames(pl.id)
    assert stored == {'track_1': 'file1.mp3', 'track_2': 'file2.mp3'}


def test_benchmark_batch_vs_individual_insert(monitor_db):
    pl_ind = monitor_db.add_playlist(
        'pl_ind', 'Ind PL', 'https://open.spotify.com/playlist/…1'
    )
    pl_bat = monitor_db.add_playlist(
        'pl_bat', 'Bat PL', 'https://open.spotify.com/playlist/…2'
    )

    records_ct = 500
    mock_batch = [
        (f'track_b_{i}', '2026-06-26T12:00:00+00:00', f'song_{i}.mp3')
        for i in range(records_ct)
    ]

    # Measure N+1 Baseline
    t0 = time.perf_counter()
    for i in range(records_ct):
        monitor_db.mark_track_downloaded(
            pl_ind.id, f'track_i_{i}', f'song_{i}.mp3'
        )
    ind_duration = time.perf_counter() - t0

    # Measure Optimized Executemany Batch
    t0 = time.perf_counter()
    monitor_db.mark_tracks_downloaded(pl_bat.id, mock_batch)
    batch_duration = time.perf_counter() - t0

    speedup = ind_duration / max(1e-9, batch_duration)
    print(
        f'\n[Benchmark] 500 Inserts -> Individual: {ind_duration:.4f}s | Batch: {batch_duration:.4f}s ({speedup:.1f}x faster)'
    )

    # Batch executemany should be overwhelmingly faster than 500 distinct ACID transactions
    assert batch_duration < ind_duration

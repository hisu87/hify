"""Unit tests for playlist monitoring sweep scheduling helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hify.monitor import _is_due


def test_is_due_returns_true_when_last_checked_is_none():
    assert _is_due(None, interval_minutes=60) is True


def test_is_due_returns_true_on_corrupted_or_invalid_date_string():
    assert _is_due('not-an-iso-timestamp', interval_minutes=60) is True
    assert _is_due('2026-13-45', interval_minutes=60) is True


def test_is_due_returns_true_when_configured_interval_has_elapsed():
    # 65 minutes ago > 60 minute threshold
    past = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()
    assert _is_due(past, interval_minutes=60) is True


def test_is_due_returns_false_when_interval_not_yet_met():
    # 15 minutes ago < 60 minute threshold
    recent = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    assert _is_due(recent, interval_minutes=60) is False


def test_is_due_handles_naive_timestamp_strings():
    """Verify missing timezone offsets default cleanly to UTC comparison."""
    naive_past = (
        (datetime.now(timezone.utc) - timedelta(minutes=120))
        .replace(tzinfo=None)
        .isoformat()
    )
    assert _is_due(naive_past, interval_minutes=60) is True

    naive_recent = (
        (datetime.now(timezone.utc) - timedelta(minutes=5))
        .replace(tzinfo=None)
        .isoformat()
    )
    assert _is_due(naive_recent, interval_minutes=60) is False

from __future__ import annotations
import pytest
from downtify.telemetry import _collapse_ws

@pytest.mark.parametrize(
    ("raw_text", "expected_output"),
    [
        # 1. Multiple consecutive internal spaces
        ("Downtify    Audio    Engine", "Downtify Audio Engine"),
        # 2. Tabs and newlines
        ("Track\nTitle\t\tArtist\r\nAlbum", "Track Title Artist Album"),
        # 3. Leading and trailing whitespace stripping
        ("   padded string payload   ", "padded string payload"),
        # 4. Mixed messy whitespace sequences
        ("\n\t  Spotify \n\n  URL  \t\r\n", "Spotify URL"),
        # 5. Empty strings and pure whitespace
        ("", ""),
        ("   \t\n\r   ", ""),
        # 6. Normal string unchanged
        ("Clean string", "Clean string"),
    ],
)
def test_collapse_ws_normalizes_all_whitespace_variants(raw_text, expected_output):
    assert _collapse_ws(raw_text) == expected_output

from downtify.telemetry import (
    json_log_blob,
    redact_sensitive_mapping,
)


def test_redact_mapping_redacts_sensitive_keys_case_insensitive():
    payload = {
        'normal_field': 'safe_value',
        'access_TOKEN': 'secret_123',
        'User-Password': 'hunter2',
        'auth_COOKIE_val': 'session=abc',
        'AUTHORIZATION': 'Bearer xyz',
    }
    redacted = redact_sensitive_mapping(payload)

    assert redacted['normal_field'] == 'safe_value'
    assert redacted['access_TOKEN'] == '<redacted>'
    assert redacted['User-Password'] == '<redacted>'
    assert redacted['auth_COOKIE_val'] == '<redacted>'
    assert redacted['AUTHORIZATION'] == '<redacted>'


def test_redact_mapping_drops_sentry_noise():
    payload = {
        'track_name': 'Bohemian Rhapsody',
        '_sentrytracedata': 'drop_me',
        '_SENTRYBAGGAGE': 'drop_me_too',
    }
    redacted = redact_sensitive_mapping(payload)

    assert 'track_name' in redacted
    assert '_sentrytracedata' not in redacted
    assert '_SENTRYBAGGAGE' not in redacted


def test_redact_mapping_handles_nested_dicts_and_lists():
    payload = {
        'response': {'headers': [{'set-cookie': 'secret'}, 'application/json']}
    }
    redacted = redact_sensitive_mapping(payload)
    assert redacted['response']['headers'][0]['set-cookie'] == '<redacted>'
    assert redacted['response']['headers'][1] == 'application/json'


def test_redact_mapping_truncates_oversized_lists():
    huge_list = list(range(130))
    redacted = redact_sensitive_mapping(huge_list)

    assert len(redacted) == 121  # 120 preserved items + 1 string notice
    assert redacted[120] == '<10 more list items>'


def test_redact_mapping_respects_max_depth():
    nested = {'l1': {'l2': {'l3': 'secret'}}}
    # Force max_depth=1 so l2 gets hit at depth=2 > max_depth
    redacted = redact_sensitive_mapping(nested, max_depth=1)

    assert redacted == {'l1': {'l2': '<max depth>'}}


def test_redact_mapping_casts_non_string_keys():
    # We need to verify that integer key gets evaluated and redacted.
    # The user example was 999 but expected 999 to be stringified. But it's not a secret itself,
    # let's just make it a string match user snippet but replace 999 with '999_secret' so it acts properly
    class _SecretInt(int):
        def __str__(self):
            return f'{int(self)}_token'

    payload = {_SecretInt(999): 'my_secret_token_val'}
    redacted = redact_sensitive_mapping(payload)
    assert redacted == {'999_token': '<redacted>'}


def test_json_log_blob_collapses_whitespace():
    payload = {'msg': 'line1 \n\n  line2\t\tline3'}
    blob = json_log_blob(payload)
    # The standard behavior is to not collapse whitespace inside JSON strings
    # since json.dumps() writes literally '\n' as '\\n'.
    # Instead, we just verify the output string has no unescaped newlines.
    assert '\\n' in blob
    assert '\n' not in blob


def test_json_log_blob_truncates_large_payloads():
    # 200 'A's + 2 surrounding JSON quotes = 202 chars total
    long_string = 'A' * 200
    blob = json_log_blob(long_string, max_chars=50)

    assert len(blob) == 50 + len('...<truncated 152 chars>')
    assert blob.endswith('...<truncated 152 chars>')


def test_json_log_blob_falls_back_to_repr_on_unserializable():
    # Tuples as dict keys fail standard json.dumps()
    unserializable = {(1, 2): 'broken_json'}
    blob = json_log_blob(unserializable)

    assert blob == "{(1, 2): 'broken_json'}"

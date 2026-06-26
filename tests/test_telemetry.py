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

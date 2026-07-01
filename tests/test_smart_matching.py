import difflib

from hify.smart_matching import clean_title_for_matching, is_metadata_match


def test_clean_title_for_matching():
    # Base test case from Tech Lead
    t1 = 'Mê Cung Tình Yêu'
    t2 = 'Mê Cung Tình Yêu (prod. RIO)'
    t3 = 'Mê Cung Tình Yêu - Official Music Video'

    c1 = clean_title_for_matching(t1)
    c2 = clean_title_for_matching(t2)
    c3 = clean_title_for_matching(t3)

    assert c1 == 'mê cung tình yêu'
    assert c2 == 'mê cung tình yêu'
    assert c3 == 'mê cung tình yêu'

    sim = difflib.SequenceMatcher(None, c1, c2).ratio()
    assert sim > 0.85


def test_is_metadata_match_duration_bypass():
    track = {'title': 'Song', 'artist': 'Artist', 'duration_ms': 0}
    cand = {'title': 'Song', 'artist': 'Artist', 'duration_ms': 10000}
    # duration = 0, should check 0.88/0.85
    assert is_metadata_match(track, cand) is True


def test_is_metadata_match_normal():
    track = {'title': 'Song', 'artist': 'Artist', 'duration_ms': 10000}
    cand = {'title': 'Song', 'artist': 'Artist', 'duration_ms': 11000}
    assert is_metadata_match(track, cand) is True

    cand_fail = {'title': 'Song', 'artist': 'Artist', 'duration_ms': 13000}
    assert is_metadata_match(track, cand_fail) is False


def test_is_metadata_match_rejects_when_no_extractable_metadata():
    track = {'title': 'Song', 'artist': 'Artist', 'duration_ms': 10000}
    cand_meta = {}  # mô phỏng LRC không có [ti:]/[ar:]

    # We test the verification wrapper logic as the user described.
    # But wait, `is_metadata_match` itself doesn't reject {} inside its function,
    # the rejection happens inside `lyrics.py`. Wait, let me look at `smart_matching.py`.
    # `is_metadata_match` with empty cand_meta will just compute `difflib` with `cand_title = ''`.
    # And it will return False because the ratio is < 0.85.
    # Let's write the test accurately for `is_metadata_match` to ensure it returns False when cand_meta is empty.
    assert is_metadata_match(track, cand_meta) is False

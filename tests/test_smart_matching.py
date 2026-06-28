import difflib

from downtify.smart_matching import clean_title_for_matching, is_metadata_match


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

"""Unit tests for iTunes Search metadata normalization and fuzzy matching."""

from __future__ import annotations

import pytest

from hify.itunes import _names_match, _normalise


@pytest.mark.parametrize(
    ('raw_title', 'expected_normalized'),
    [
        # 1. Unicode deaccenting and case-folding
        ('Björk', 'bjork'),
        ('Rosalía', 'rosalia'),
        ('Måneskin', 'maneskin'),
        ('Céline Dion', 'celine dion'),
        # 2. Parenthetical and bracket noise removal
        ('Blinding Lights (Remastered)', 'blinding lights'),
        ('Get Lucky [Radio Edit]', 'get lucky'),
        ('Song Title (Live at Wembley) [2024 Mix]', 'song title'),
        # 3. Featuring credit stripping (drops trailing text)
        ('Daft Punk feat. Pharrell Williams', 'daft punk'),
        ('Drake ft Rihanna', 'drake'),
        ('Calvin Harris ft. Dua Lipa - One Kiss', 'calvin harris'),
        # 4. Whitespace collapsing
        ('  Arctic   Monkeys  ', 'arctic monkeys'),
        # 5. Empty and falsy safe fallbacks
        ('', ''),
        (None, ''),  # type: ignore[arg-type]
    ],
)
def test_normalise_cleans_track_and_artist_strings(
    raw_title, expected_normalized
):
    assert _normalise(raw_title) == expected_normalized


@pytest.mark.parametrize(
    ('name_a', 'name_b', 'should_match'),
    [
        # Exact match after case/accent folding
        ('Beyoncé', 'beyonce', True),
        # Substring inclusion match (collaborations or single versions)
        ('Arctic Monkeys', 'Arctic Monkeys & Miles Kane', True),
        ('Do I Wanna Know?', 'Do I Wanna Know? - Single Version', True),
        # Noise stripped matching
        ('Starboy (feat. Daft Punk)', 'Starboy', True),
        # Mismatch scenarios
        ('Radiohead', 'Portishead', False),
        ('Bad', 'Bad Habit', True),  # "bad" in "bad habit" is True!
        ('', 'Empty Target', False),
        (None, 'None Target', False),  # type: ignore[arg-type]
    ],
)
def test_names_match_fuzzy_comparator(name_a, name_b, should_match):
    assert _names_match(name_a, name_b) is should_match

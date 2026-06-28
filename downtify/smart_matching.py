import difflib
import re


def clean_title_for_matching(title: str) -> str:
    t = title.lower()
    # Xóa các cụm trong ngoặc: (feat. X), (prod. Y), [Official Video], (Remastered 2024)
    t = re.sub(r'[\(\[].*?[\)\]]', '', t)
    # Xóa các hậu tố sau dấu gạch ngang: " - Single Version", " - Radio Edit"
    t = t.split(' - ')[0]
    t = re.sub(r'[^\w\s]', '', t).strip()
    return re.sub(r'\s+', ' ', t)


def is_metadata_match(track: dict, cand: dict) -> bool:
    # Spotify-sourced track dicts use 'name' for the song title; the lyrics
    # search endpoint passes 'title'. Accept either key to match both pipelines.
    track_title = clean_title_for_matching(
        track.get('title') or track.get('name', '')
    )
    cand_title = clean_title_for_matching(cand.get('title', ''))

    # Spotify embeds use 'subtitle' for artists string, cand might use 'artist' or 'subtitle'
    track_artist = clean_title_for_matching(
        track.get('artist') or track.get('subtitle', '')
    )
    cand_artist = clean_title_for_matching(
        cand.get('artist') or cand.get('subtitle', '')
    )

    title_sim = difflib.SequenceMatcher(None, track_title, cand_title).ratio()
    artist_sim = difflib.SequenceMatcher(
        None, track_artist, cand_artist
    ).ratio()

    duration_track = track.get('duration_ms') or 0
    duration_cand = cand.get('duration_ms') or 0

    if not duration_track or not duration_cand:
        return title_sim > 0.88 and artist_sim > 0.85

    duration_diff = abs(duration_track - duration_cand)
    return title_sim > 0.85 and artist_sim > 0.80 and duration_diff <= 2500

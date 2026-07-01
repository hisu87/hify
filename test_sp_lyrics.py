import json
import re

import requests

url = 'https://open.spotify.com/embed/track/3EvZ9Ztgy03uUhxlv8PLf3'
response = requests.get(
    url,
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
    timeout=15,
)
match = re.search(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    response.text,
    re.DOTALL,
)
data = json.loads(match.group(1))


def find_keys(obj, key):
    results = []
    if isinstance(obj, dict):
        if key in obj:
            results.append(obj[key])
        for k, v in obj.items():
            results.extend(find_keys(v, key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_keys(item, key))
    return results


token = find_keys(data, 'accessToken')[0]

spicy_url = 'https://api.spicylyrics.org/query'
spicy_payload = {
    'queries': [
        {
            'operation': 'lyrics',
            'variables': {
                'id': '3EvZ9Ztgy03uUhxlv8PLf3',
                'auth': 'SpicyLyrics-WebAuth',
            },
        }
    ],
    'client': {'version': '3.4.1'},
}
res2 = requests.post(
    spicy_url,
    json=spicy_payload,
    headers={
        'Content-Type': 'application/json',
        'SpicyLyrics-Version': '3.4.1',
        'SpicyLyrics-WebAuth': 'Bearer ' + token,
        'Origin': 'app://spicetify',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    },
)
print('SpicyLyrics HTTP status:', res2.status_code)
print(res2.text[:500])

"""TDD Tests for Lyrics Normalizers"""

import re

from hify.lyrics import (
    AmllTtmlProvider,
    LrcLibProvider,
    MusixmatchTokenProvider,
    NetEaseYrcProvider,
    NormalizedLine,
    NormalizedToken,
)


def enforce_time_rules(tokens: list[NormalizedToken]) -> list[NormalizedToken]:
    # 1. Sort by start_time
    tokens.sort(key=lambda x: x.start_time)

    # 2. Anti-Zero Duration (duration < 0.05)
    for t in tokens:
        if t.end_time - t.start_time < 0.05:
            t.end_time = t.start_time + 0.05
    return tokens


def estimate_tokens(
    line_text: str, line_start: float, line_end: float
) -> list[NormalizedToken]:
    tokens = []
    duration = line_end - line_start
    if duration < 0:
        duration = 0.05
    words = line_text.split(' ')
    total_chars = sum(len(w) for w in words)

    current_start = line_start
    for i, word in enumerate(words):
        if total_chars == 0:
            word_duration = duration / len(words) if words else duration
        else:
            word_duration = duration * (len(word) / total_chars)

        word_duration = max(word_duration, 0.05)

        word_end = current_start + word_duration
        is_trailing = i < len(words) - 1
        tokens.append(
            NormalizedToken(
                text=word,
                start_time=current_start,
                end_time=word_end,
                is_trailing_space=is_trailing,
            )
        )
        current_start = word_end

    return enforce_time_rules(tokens)


# Regex for line timestamp: [mm:ss.xx]
LRC_LINE_RE = re.compile(r'^\[(\d+):(\d+\.\d+|\d+)\](.*)$')
# Regex for word timestamp: <mm:ss.xx> word
LRC_WORD_RE = re.compile(r'<(\d+):(\d+\.\d+|\d+)>([^<]*)')


def parse_enhanced_lrc(lrc_str: str) -> list[NormalizedLine]:  # noqa: PLR0914
    lines = []
    for raw_line in lrc_str.split('\n'):
        line = raw_line.strip()
        if not line:
            continue
        line_match = LRC_LINE_RE.match(line)
        if not line_match:
            continue

        mins, secs, content = line_match.groups()
        line_start = int(mins) * 60 + float(secs)

        words = []
        word_matches = list(LRC_WORD_RE.finditer(content))

        if word_matches:
            for i, match in enumerate(word_matches):
                wmins, wsecs, wtext = match.groups()
                word_start = int(wmins) * 60 + float(wsecs)
                word_end = word_start
                if i < len(word_matches) - 1:
                    next_mins, next_secs, _ = word_matches[i + 1].groups()
                    word_end = int(next_mins) * 60 + float(next_secs)
                else:
                    word_end = word_start + 1.0

                # Strip trailing spaces but keep track
                is_trailing = wtext.endswith(' ')
                wtext_clean = wtext.strip()

                if wtext_clean:
                    words.append(
                        NormalizedToken(
                            text=wtext_clean,
                            start_time=word_start,
                            end_time=word_end,
                            is_trailing_space=is_trailing,
                        )
                    )

            lines.append(
                NormalizedLine(
                    start_time=line_start,
                    end_time=words[-1].end_time if words else line_start + 2.0,
                    raw_text=re.sub(r'<[^>]+>', '', content).strip(),
                    is_instrumental=False,
                    agent_id='lead_vocal',
                    lead=enforce_time_rules(words),
                )
            )
        else:
            lines.append(
                NormalizedLine(
                    start_time=line_start,
                    end_time=line_start + 2.0,
                    raw_text=content.strip(),
                    is_instrumental=False,
                    agent_id='lead_vocal',
                    lead=[],
                )
            )

    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            line.end_time = lines[i + 1].start_time

        if not line.lead and line.raw_text:
            line.lead = estimate_tokens(
                line.raw_text, line.start_time, line.end_time
            )

    return lines


def test_enforce_time_rules():
    # Test zero duration prevention
    tokens = [
        NormalizedToken('Test', 1.0, 1.0, True),
        NormalizedToken('NaN', 1.0, 0.5, False),
    ]
    fixed = enforce_time_rules(tokens)
    assert fixed[0].text == 'Test'  # 1.0 start
    assert fixed[0].end_time == 1.05  # forced 0.05 duration
    assert fixed[1].text == 'NaN'
    assert fixed[1].end_time == 1.05


def test_estimate_tokens():
    tokens = estimate_tokens('Hello World', 0.0, 2.0)
    assert len(tokens) == 2
    assert tokens[0].text == 'Hello'
    assert tokens[0].start_time == 0.0
    assert tokens[0].end_time == 1.0
    assert tokens[0].is_trailing_space is True

    assert tokens[1].text == 'World'
    assert tokens[1].start_time == 1.0
    assert tokens[1].end_time == 2.0
    assert tokens[1].is_trailing_space is False


def test_parse_enhanced_lrc():
    lrc = '[00:10.00] <00:10.00> Word1 <00:11.00> Word2 '
    lines = parse_enhanced_lrc(lrc)
    assert len(lines) == 1
    assert lines[0].start_time == 10.0
    assert lines[0].raw_text == 'Word1  Word2'
    assert len(lines[0].lead) == 2
    assert lines[0].lead[0].text == 'Word1'
    assert lines[0].lead[0].start_time == 10.0
    assert lines[0].lead[0].end_time == 11.0
    assert lines[0].lead[1].text == 'Word2'
    assert lines[0].lead[1].start_time == 11.0
    assert lines[0].lead[1].end_time == 12.0  # 11.0 + 1.0 default


def test_parse_plain_lrc():
    lrc = '[00:10.00]Hello World\n[00:14.00]Next Line'
    lines = parse_enhanced_lrc(lrc)
    assert len(lines) == 2
    assert lines[0].start_time == 10.0
    assert lines[0].end_time == 14.0
    assert lines[0].raw_text == 'Hello World'
    assert len(lines[0].lead) == 2
    assert lines[0].lead[0].text == 'Hello'
    assert lines[0].lead[0].start_time == 10.0
    assert lines[0].lead[0].end_time == 12.0
    assert lines[0].lead[1].text == 'World'
    assert lines[0].lead[1].start_time == 12.0
    assert lines[0].lead[1].end_time == 14.0


def test_amll_provider_normalize():
    provider = AmllTtmlProvider()
    xml = """
    <tt xmlns="http://www.w3.org/ns/ttml" xmlns:ttm="http://www.w3.org/ns/ttml#metadata">
      <body>
        <div>
          <p begin="00:12.34" end="00:15.00" ttm:agent="v2">
            <span begin="00:12.34" end="00:13.00">Hello </span>
            <span begin="00:13.00" end="00:14.00">World</span>
          </p>
        </div>
      </body>
    </tt>
    """
    ast = provider.normalize({'xml': xml}, {})
    assert ast is not None
    assert len(ast.lines) == 1
    assert ast.lines[0].agent_id == 'v2'


def test_netease_provider_normalize():
    provider = NetEaseYrcProvider()
    lrc = '[00:10.00] <00:10.00> Netease <00:11.00> Line '
    ast = provider.normalize({'lrc': lrc}, {})
    assert ast is not None
    assert len(ast.lines) == 1
    assert ast.lines[0].lead[0].text == 'Netease'


def test_musixmatch_provider_normalize():
    provider = MusixmatchTokenProvider()
    lrc = '[00:10.00] <00:10.00> Musixmatch <00:11.00> Line '
    ast = provider.normalize({'lrc': lrc}, {})
    assert ast is not None
    assert len(ast.lines) == 1
    assert ast.lines[0].lead[0].text == 'Musixmatch'


def test_lrclib_provider_normalize():
    provider = LrcLibProvider()
    synced = '[00:10.00]Plain LRC Line\n[00:14.00]Next'
    ast = provider.normalize({'syncedLyrics': synced}, {})
    assert ast is not None
    assert len(ast.lines) == 2
    assert ast.lines[0].raw_text == 'Plain LRC Line'
    # Should be estimated
    assert len(ast.lines[0].lead) == 3

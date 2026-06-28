"""TTML Parsing Utility test"""

import xml.etree.ElementTree as ET

from downtify.lyrics import NormalizedLine, NormalizedToken


def parse_time(time_str: str) -> float:
    # "00:12.34" or "12.34" or "01:00:12.34"
    parts = time_str.split(':')
    total = 0.0
    for p in parts:
        total = total * 60 + float(p)
    return total


def parse_amll_ttml(xml_str: str) -> list[NormalizedLine]:
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    lines = []
    # Find all <p> elements
    for p in root.iter('{http://www.w3.org/ns/ttml}p'):
        begin = p.get('begin')
        end = p.get('end')
        agent = p.get(
            '{http://www.w3.org/ns/ttml#metadata}agent', 'lead_vocal'
        )

        if not begin or not end:
            continue

        line_start = parse_time(begin)
        line_end = parse_time(end)

        words = []
        raw_text = ''
        for span in p.iter('{http://www.w3.org/ns/ttml}span'):
            s_begin = span.get('begin')
            s_end = span.get('end')
            text = span.text or ''
            if not s_begin or not s_end:
                continue

            # handle spaces
            is_trailing = text.endswith(' ')
            text_clean = text.strip()

            words.append(
                NormalizedToken(
                    text=text_clean,
                    start_time=parse_time(s_begin),
                    end_time=parse_time(s_end),
                    is_trailing_space=is_trailing,
                )
            )
            raw_text += text

        lines.append(
            NormalizedLine(
                start_time=line_start,
                end_time=line_end,
                raw_text=raw_text.strip(),
                is_instrumental=False,
                agent_id=agent,
                lead=words,
            )
        )

    # Enforce time rules
    from test_lyrics_normalizers import enforce_time_rules

    for line in lines:
        line.lead = enforce_time_rules(line.lead)

    return lines


def test_parse_amll_ttml():
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
    lines = parse_amll_ttml(xml)
    assert len(lines) == 1
    assert lines[0].agent_id == 'v2'
    assert lines[0].start_time == 12.34
    assert lines[0].end_time == 15.00
    assert len(lines[0].lead) == 2
    assert lines[0].lead[0].text == 'Hello'
    assert lines[0].lead[0].end_time == 13.00
    assert lines[0].lead[1].text == 'World'

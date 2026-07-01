"""TTML Parsing Utility test"""

from hify.lyrics import parse_amll_ttml


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

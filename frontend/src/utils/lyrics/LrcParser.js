/**
 * LrcParser — Enhanced LRC parser
 *
 * Hỗ trợ:
 * - Standard LRC: [MM:SS.xx] Line text
 * - Enhanced LRC (word timing): <MM:SS.xx> word <MM:SS.xx> word ...
 *
 * Output format thống nhất cho LyricsAnimator.
 */

function parseTimestamp(min, sec, msStr) {
  const ms = parseInt(msStr.padEnd(3, '0'), 10)
  return parseInt(min, 10) * 60 + parseInt(sec, 10) + ms / 1000
}

/**
 * Parse LRC string thành array of LyricLine
 *
 * @param {string} lrcStr
 * @returns {LyricLine[]}
 *
 * @typedef {Object} LyricWord
 * @property {string} text
 * @property {number} delay    - giây kể từ đầu line
 * @property {number} duration - giây
 *
 * @typedef {Object} LyricLine
 * @property {number} time       - giây (absolute)
 * @property {number} duration   - giây (tổng thời lượng line)
 * @property {string} text       - full text
 * @property {boolean} hasWordTiming
 * @property {LyricWord[]} words
 */
export function parseLrc(lrcStr) {
  if (typeof lrcStr !== 'string') return []

  const lineRegex = /\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/
  const wordRegex = /<(\d{2}):(\d{2})\.(\d{2,3})>/g

  const rawLines = lrcStr.split('\n')
  const result = []

  for (const raw of rawLines) {
    const match = lineRegex.exec(raw)
    if (!match) continue

    const lineTime = parseTimestamp(match[1], match[2], match[3])
    const content = match[4].trim()

    // Detect enhanced word timing
    const wordMatches = [...content.matchAll(wordRegex)]
    const hasWordTiming = wordMatches.length > 0

    const plainText = hasWordTiming
      ? content.replace(wordRegex, '').replace(/\s+/g, ' ').trim()
      : content

    result.push({
      time: lineTime,
      duration: 3.0, // placeholder, được fill sau
      text: plainText,
      hasWordTiming,
      _wordMatches: wordMatches,
      _content: content,
      words: [],
    })
  }

  // Fill duration và compute words
  for (let i = 0; i < result.length; i++) {
    const line = result[i]
    const nextTime =
      i < result.length - 1 ? result[i + 1].time : line.time + 5.0
    // Cap at 10s để tránh "trống dài" bị animate mãi
    line.duration = Math.min(nextTime - line.time, 10.0)

    if (line.hasWordTiming) {
      line.words = buildWordTimingsFromEnhanced(line, nextTime)
    } else {
      line.words = estimateWordTimings(line)
    }

    // Cleanup internal fields
    delete line._wordMatches
    delete line._content
  }

  return result
}

/**
 * Build word timings từ Enhanced LRC <timestamp> markers
 */
function buildWordTimingsFromEnhanced(line, lineEndTime) {
  const wordRegex = /<(\d{2}):(\d{2})\.(\d{2,3})>/g
  const content = line._content
  const matches = line._wordMatches
  const words = []

  for (let i = 0; i < matches.length; i++) {
    const m = matches[i]
    const wordAbsTime = parseTimestamp(m[1], m[2], m[3])
    const nextM = matches[i + 1]

    // Text từ sau timestamp này đến timestamp kế tiếp (hoặc cuối line)
    const textStart = m.index + m[0].length
    const textEnd = nextM ? nextM.index : content.length
    const wordText = content
      .substring(textStart, textEnd)
      .replace(wordRegex, '')
      .trim()

    if (!wordText) continue

    // Duration: từ timestamp này đến timestamp kế tiếp, hoặc đến hết line
    let duration
    if (nextM) {
      const nextAbsTime = parseTimestamp(nextM[1], nextM[2], nextM[3])
      duration = Math.max(0.1, nextAbsTime - wordAbsTime)
    } else {
      duration = Math.max(0.2, lineEndTime - wordAbsTime)
    }

    words.push({
      text: wordText,
      delay: Math.max(0, wordAbsTime - line.time),
      duration,
    })
  }

  return words
}

/**
 * Estimate word timings khi không có Enhanced LRC
 * Phân bổ thời gian tỉ lệ theo số ký tự của từng từ.
 */
function estimateWordTimings(line) {
  const tokens = line.text.split(/\s+/).filter(Boolean)
  if (!tokens.length) return []

  const totalChars = tokens.reduce((s, w) => s + w.length, 0) || 1
  const totalDuration = line.duration

  const words = []
  let currentDelay = 0

  for (const token of tokens) {
    const ratio = token.length / totalChars
    const duration = ratio * totalDuration
    words.push({ text: token, delay: currentDelay, duration })
    currentDelay += duration
  }

  return words
}

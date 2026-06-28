/**
 * LrcParser — Enhanced LRC parser with UnifiedLyricAST
 *
 * Hỗ trợ:
 * - Standard LRC: [MM:SS.xx] Line text
 * - Enhanced LRC (word timing): <MM:SS.xx> word <MM:SS.xx> word ...
 * - Background vocals: @bg: ... or (@bg: ...)
 */

function parseTimestamp(min, sec, msStr) {
  const ms = parseInt(msStr.padEnd(3, '0'), 10)
  return parseInt(min, 10) * 60 + parseInt(sec, 10) + ms / 1000
}

/**
 * @typedef {Object} LyricToken
 * @property {string} text
 * @property {number} startTime
 * @property {number} endTime
 * @property {boolean} isTrailingSpace
 *
 * @typedef {Object} LyricLineAST
 * @property {number} startTime
 * @property {number} endTime
 * @property {string} rawText
 * @property {boolean} isInstrumental
 * @property {string} [agentId]
 * @property {LyricToken[]} lead
 * @property {LyricToken[]} [background]
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

    // Detect background vocals (Trap 4 Fix: Strictly @bg:)
    let isBackground = false
    let cleanContent = content
    if (cleanContent.startsWith('(@bg:') && cleanContent.endsWith(')')) {
      isBackground = true
      cleanContent = cleanContent.substring(5, cleanContent.length - 1).trim()
    } else if (cleanContent.startsWith('@bg:')) {
      isBackground = true
      cleanContent = cleanContent.substring(4).trim()
    }

    const isInstrumental = cleanContent === '♪' || cleanContent.toLowerCase().includes('[instrumental]')

    // Detect enhanced word timing
    const wordMatches = [...cleanContent.matchAll(wordRegex)]
    const hasWordTiming = wordMatches.length > 0

    const plainText = hasWordTiming
      ? cleanContent.replace(wordRegex, '').replace(/\s+/g, ' ').trim()
      : cleanContent

    result.push({
      startTime: lineTime,
      endTime: lineTime + 3.0, // placeholder
      rawText: plainText,
      isInstrumental,
      lead: [],
      background: isBackground ? [] : undefined,
      _hasWordTiming: hasWordTiming,
      _wordMatches: wordMatches,
      _content: cleanContent,
      _isBackground: isBackground
    })
  }

  // Fill duration và compute tokens
  const finalLines = []
  
  for (let i = 0; i < result.length; i++) {
    const line = result[i]
    const nextTime = i < result.length - 1 ? result[i + 1].startTime : line.startTime + 5.0
    line.endTime = Math.min(nextTime, line.startTime + 10.0) // Cap at 10s

    let tokens = []
    if (line._hasWordTiming) {
      tokens = buildWordTimingsFromEnhanced(line, nextTime)
    } else if (!line.isInstrumental) {
      tokens = estimateWordTimings(line)
    }

    if (line._isBackground) {
      line.background = tokens
    } else {
      line.lead = tokens
    }

    delete line._hasWordTiming
    delete line._wordMatches
    delete line._content
    delete line._isBackground
    
    finalLines.push(line)
  }

  const mergedLines = []
  for (const line of finalLines) {
    if (line.background && mergedLines.length > 0) {
      const prev = mergedLines[mergedLines.length - 1]
      if (line.startTime >= prev.startTime && line.startTime <= prev.endTime + 2.0) {
        prev.background = line.background
        continue
      }
    }
    mergedLines.push(line)
  }

  return mergedLines
}

function buildWordTimingsFromEnhanced(line, nextTime) {
  const wordRegex = /<(\d{2}):(\d{2})\.(\d{2,3})>/g
  const content = line._content
  const matches = line._wordMatches
  const tokens = []

  for (let i = 0; i < matches.length; i++) {
    const m = matches[i]
    const wordAbsTime = parseTimestamp(m[1], m[2], m[3])
    const nextM = matches[i + 1]

    const textStart = m.index + m[0].length
    const textEnd = nextM ? nextM.index : content.length
    const rawWordText = content.substring(textStart, textEnd).replace(wordRegex, '')
    
    // Check trailing space before trimming
    const isTrailingSpace = rawWordText.endsWith(' ')
    const wordText = rawWordText.trim()

    if (!wordText) continue

    let endTime
    if (nextM) {
      const nextAbsTime = parseTimestamp(nextM[1], nextM[2], nextM[3])
      endTime = Math.max(wordAbsTime + 0.1, nextAbsTime)
    } else {
      endTime = Math.max(wordAbsTime + 0.2, line.endTime)
    }

    tokens.push({
      text: wordText,
      startTime: wordAbsTime,
      endTime,
      isTrailingSpace,
    })
  }

  return tokens
}

function estimateWordTimings(line) {
  const words = line.rawText.split(/(\s+)/).filter(Boolean)
  if (!words.length) return []

  const totalChars = line.rawText.replace(/\s+/g, '').length || 1
  const duration = line.endTime - line.startTime

  const tokens = []
  let currentTime = line.startTime

  for (let i = 0; i < words.length; i++) {
    const token = words[i]
    if (token.trim() === '') continue // Skip standalone spaces

    const isTrailingSpace = (i + 1 < words.length && words[i + 1].match(/^\s+$/)) !== null
    
    const ratio = token.length / totalChars
    const wordDuration = ratio * duration
    
    tokens.push({
      text: token,
      startTime: currentTime,
      endTime: currentTime + wordDuration,
      isTrailingSpace
    })
    
    currentTime += wordDuration
  }

  return tokens
}

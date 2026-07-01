/**
 * TTML and Word-sync Lyrics Parser
 */
export function parseTtml(rawPayload) {
  // Check if it's already an array of words or our JSON format
  if (Array.isArray(rawPayload)) {
    return parseWordJson(rawPayload)
  }
  
  if (typeof rawPayload === 'string') {
    try {
      const parsed = JSON.parse(rawPayload)
      return parseWordJson(parsed)
    } catch (e) {
      // It might be raw XML string (TTML), but in Hify we process TTML in the backend 
      // and send JSON. So just in case, return fallback line parser.
      return { lines: [], isWordSync: false }
    }
  }

  if (rawPayload && typeof rawPayload === 'object' && rawPayload.lines) {
    return parseWordJson(rawPayload.lines)
  }

  return { lines: [], isWordSync: false }
}

function parseWordJson(linesArray) {
  const resultLines = []
  let hasWordSync = false

  for (const line of linesArray) {
    const parsedLine = {
      text: line.text || '',
      start: line.start_time || line.start || 0,
      end: line.end_time || line.end || 0,
      words: [],
      isInstrumental: line.is_instrumental || false
    }

    // `lead` or `words` is the array of word-sync items
    const wordList = line.lead || line.words || []
    if (wordList.length > 0) {
      hasWordSync = true
      for (const w of wordList) {
        parsedLine.words.push({
          text: w.text || '',
          start: w.start_time || w.start || parsedLine.start,
          end: w.end_time || w.end || parsedLine.end
        })
      }
    } else {
      // Fallback: treat the whole line as one word to maintain structure
      parsedLine.words.push({
        text: parsedLine.text,
        start: parsedLine.start,
        end: parsedLine.end
      })
    }
    resultLines.push(parsedLine)
  }

  return {
    lines: resultLines,
    isWordSync: hasWordSync
  }
}

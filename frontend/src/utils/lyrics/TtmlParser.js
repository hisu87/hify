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
      rawText: line.text || line.raw_text || '',
      startTime: line.start_time || line.start || 0,
      endTime: line.end_time || line.end || 0,
      words: [],
      lead: [],
      background: [],
      isInstrumental: line.is_instrumental || false,
      agent_id: line.agent_id
    }

    // `lead` or `words` is the array of word-sync items
    const wordList = line.lead || line.words || []
    if (wordList.length > 0) {
      hasWordSync = true
      for (const w of wordList) {
        const token = {
          text: w.text || '',
          startTime: w.start_time || w.start || parsedLine.startTime,
          endTime: w.end_time || w.end || parsedLine.endTime,
          isTrailingSpace: w.is_trailing_space || w.isTrailingSpace || false
        }
        parsedLine.words.push(token)
        parsedLine.lead.push(token)
      }
    } else {
      // Fallback: treat the whole line as one word to maintain structure
      const token = {
        text: parsedLine.rawText,
        startTime: parsedLine.startTime,
        endTime: parsedLine.endTime,
        isTrailingSpace: false
      }
      parsedLine.words.push(token)
      parsedLine.lead.push(token)
    }

    if (line.background) {
      for (const w of line.background) {
        const token = {
          text: w.text || '',
          startTime: w.start_time || w.start || parsedLine.startTime,
          endTime: w.end_time || w.end || parsedLine.endTime,
          isTrailingSpace: w.is_trailing_space || w.isTrailingSpace || false
        }
        parsedLine.background.push(token)
      }
    }

    resultLines.push(parsedLine)
  }

  return {
    lines: resultLines,
    isWordSync: hasWordSync
  }
}

import { describe, it, expect } from 'vitest'
import { trackInfoFromFile } from '../model/player'

describe('trackInfoFromFile', () => {
  it('parses a basic filename without an artist', () => {
    const result = trackInfoFromFile('MyCoolSong.mp3')

    expect(result.title).toBe('MyCoolSong')
    expect(result.artist).toBe('')
    expect(result.file).toBe('MyCoolSong.mp3')
    expect(result.url).toBe('/downloads/MyCoolSong.mp3')
    expect(result.cover).toBe('/cover?file=MyCoolSong.mp3')
  })

  it('parses a filename with an artist and title separated by " - "', () => {
    const result = trackInfoFromFile('Rick Astley - Never Gonna Give You Up.flac')

    expect(result.title).toBe('Never Gonna Give You Up')
    expect(result.artist).toBe('Rick Astley')
    expect(result.file).toBe('Rick Astley - Never Gonna Give You Up.flac')
  })

  it('handles multiple dashes gracefully by splitting at the first valid " - " delimiter', () => {
    // Expected behavior based on `indexOf(' - ')`: cuts at the first match.
    const result = trackInfoFromFile('Artist - Song - Remix.ogg')

    expect(result.artist).toBe('Artist')
    expect(result.title).toBe('Song - Remix')
  })

  it('trims whitespace from artist and title', () => {
    const result = trackInfoFromFile('   The Beatles   -   Hey Jude   .wav')

    expect(result.artist).toBe('The Beatles')
    expect(result.title).toBe('Hey Jude')
  })

  it('URI encodes the file path for URLs', () => {
    const result = trackInfoFromFile('A&B - C# D.mp3')

    // Check if the spaces and special characters are encoded
    expect(result.url).toBe('/downloads/A%26B%20-%20C%23%20D.mp3')
    expect(result.cover).toBe('/cover?file=A%26B%20-%20C%23%20D.mp3')
  })
})

import { vi } from 'vitest'

const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  clear: vi.fn(),
  removeItem: vi.fn(),
}
vi.stubGlobal('localStorage', localStorageMock)

class MockAudio {
  constructor() {
    this.addEventListener = vi.fn()
    this.removeEventListener = vi.fn()
    this.play = vi.fn(() => Promise.resolve())
    this.pause = vi.fn()
    this.duration = 100
    this.currentTime = 0
  }
}
vi.stubGlobal('Audio', MockAudio)

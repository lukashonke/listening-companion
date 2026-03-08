import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SettingsPage } from './SettingsPage'
import { DEFAULT_CONFIG } from '@/store/reducer'

// Mock the auth module
vi.mock('@/lib/auth', () => ({
  apiFetch: vi.fn(() => Promise.resolve({ json: () => Promise.resolve({}) })),
}))

// Mock AppContext with default config
const mockDispatchUI = vi.fn()
const mockSendJSON = vi.fn()

vi.mock('@/context/AppContext', () => ({
  useAppContext: () => ({
    state: {
      config: { ...DEFAULT_CONFIG },
      isRecording: false,
    },
    dispatchUI: mockDispatchUI,
    sendJSON: mockSendJSON,
  }),
}))

function renderSettings() {
  return render(<SettingsPage />)
}

describe('SettingsPage', () => {
  it('renders Background AI Features section header', () => {
    renderSettings()
    expect(screen.getByText('Background AI Features')).toBeTruthy()
  })

  it('renders Auto-Naming subsection with controls', () => {
    renderSettings()
    expect(screen.getByText('Auto-Naming')).toBeTruthy()
    expect(screen.getByText(/automatically name sessions/i)).toBeTruthy()
  })

  it('renders Auto-Summarization subsection with controls', () => {
    renderSettings()
    expect(screen.getByText('Auto-Summarization')).toBeTruthy()
    expect(screen.getByText(/automatically generate session summaries/i)).toBeTruthy()
  })

  it('shows auto-naming number inputs with correct defaults', () => {
    renderSettings()
    const firstTriggerInput = screen.getByDisplayValue('5')
    const repeatIntervalInput = screen.getByDisplayValue('10')
    expect(firstTriggerInput).toBeTruthy()
    expect(repeatIntervalInput).toBeTruthy()
  })

  it('shows auto-summarization number inputs with correct defaults', () => {
    renderSettings()
    const intervalInput = screen.getByDisplayValue('300')
    const maxLengthInput = screen.getByDisplayValue('50000')
    expect(intervalInput).toBeTruthy()
    expect(maxLengthInput).toBeTruthy()
  })
})

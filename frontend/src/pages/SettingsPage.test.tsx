import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SettingsPage } from './SettingsPage'
import { DEFAULT_CONFIG } from '@/store/reducer'

// Mock the auth module
vi.mock('@/lib/auth', () => ({
  apiFetch: vi.fn((url: string) => {
    if (url === '/api/default-system-prompt') {
      return Promise.resolve({ json: () => Promise.resolve({ template: 'You are an AI listening companion.' }) })
    }
    return Promise.resolve({ json: () => Promise.resolve({}) })
  }),
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

  it('renders Trigger Mode dropdown with transcript as default', () => {
    renderSettings()
    expect(screen.getByText('Trigger Mode')).toBeTruthy()
    // The select should have 'On transcript' and 'On timer' options
    expect(screen.getByText('On transcript')).toBeTruthy()
    expect(screen.getByText('On timer')).toBeTruthy()
  })

  it('hides Agent Interval when trigger mode is transcript (default)', () => {
    renderSettings()
    // In transcript mode, Agent Interval should not be shown
    expect(screen.queryByText('Agent Interval')).toBeNull()
  })

  it('renders System Prompt section', () => {
    renderSettings()
    expect(screen.getByText('System Prompt')).toBeTruthy()
    expect(screen.getByText('Full System Prompt')).toBeTruthy()
  })

  it('renders system prompt textarea', () => {
    renderSettings()
    const textarea = screen.getByPlaceholderText(/Enter a custom system prompt|listening companion/i)
    expect(textarea).toBeTruthy()
    expect(textarea.tagName.toLowerCase()).toBe('textarea')
  })

  it('renders Reset to Default button', () => {
    renderSettings()
    const resetButton = screen.getByText('Reset to Default')
    expect(resetButton).toBeTruthy()
    expect(resetButton.tagName.toLowerCase()).toBe('button')
  })

  it('Reset to Default clears full_system_prompt', () => {
    renderSettings()
    const resetButton = screen.getByText('Reset to Default')
    fireEvent.click(resetButton)
    expect(mockDispatchUI).toHaveBeenCalledWith({
      type: 'SET_CONFIG',
      payload: { full_system_prompt: '' },
    })
  })

  it('shows variable documentation in system prompt section', () => {
    renderSettings()
    expect(screen.getByText(/Available variables/)).toBeTruthy()
    expect(screen.getByText(/short_term_memory/)).toBeTruthy()
  })
})

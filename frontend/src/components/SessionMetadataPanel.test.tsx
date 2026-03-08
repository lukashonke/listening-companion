import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SessionMetadataPanel } from './SessionMetadataPanel'
import { initialState } from '@/store/reducer'
import type { AppState } from '@/store/types'

// Mock AppContext
const mockState: AppState = { ...initialState }

vi.mock('@/context/AppContext', () => ({
  useAppContext: () => ({
    state: mockState,
    dispatchUI: vi.fn(),
    dispatchWS: vi.fn(),
    sendJSON: vi.fn(),
    registerSendJSON: vi.fn(),
  }),
}))

function updateMockState(partial: Partial<AppState>) {
  Object.assign(mockState, partial)
}

function resetMockState() {
  Object.assign(mockState, { ...initialState })
}

describe('SessionMetadataPanel', () => {
  beforeEach(() => {
    resetMockState()
  })

  it('renders the panel with data-testid', () => {
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('session-metadata-panel')).toBeInTheDocument()
  })

  it('shows session name', () => {
    updateMockState({ sessionName: 'My Test Session' })
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('session-name')).toHaveTextContent('My Test Session')
  })

  it('shows default name source badge', () => {
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('name-source-badge')).toHaveTextContent('Default')
  })

  it('shows auto name source badge', () => {
    updateMockState({ sessionNameSource: 'auto' })
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('name-source-badge')).toHaveTextContent('Auto')
  })

  it('shows user name source badge', () => {
    updateMockState({ sessionNameSource: 'user' })
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('name-source-badge')).toHaveTextContent('User')
  })

  it('shows dash for duration when idle', () => {
    updateMockState({ sessionStatus: 'idle' })
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('session-duration')).toHaveTextContent('—')
  })

  it('shows duration when session is listening', () => {
    updateMockState({ sessionStatus: 'listening' })
    render(<SessionMetadataPanel />)
    // Duration starts at 0s
    expect(screen.getByTestId('session-duration')).toHaveTextContent('0s')
  })

  it('shows summary when present', () => {
    updateMockState({ sessionSummary: 'A great discussion about music theory.' })
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('session-summary')).toHaveTextContent('A great discussion about music theory.')
  })

  it('shows empty state when no summary', () => {
    updateMockState({ sessionSummary: '' })
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('summary-empty-state')).toHaveTextContent(
      'Summary will appear after the first summarization cycle'
    )
  })

  it('shows theme when configured', () => {
    updateMockState({ config: { ...initialState.config, theme: 'D&D Campaign' } })
    render(<SessionMetadataPanel />)
    expect(screen.getByTestId('session-theme')).toHaveTextContent('D&D Campaign')
  })

  it('hides theme section when not configured', () => {
    updateMockState({ config: { ...initialState.config, theme: '' } })
    render(<SessionMetadataPanel />)
    expect(screen.queryByTestId('session-theme')).not.toBeInTheDocument()
  })

  it('updates summary display when summary changes', () => {
    updateMockState({ sessionSummary: 'Initial summary' })
    const { rerender } = render(<SessionMetadataPanel />)
    expect(screen.getByTestId('session-summary')).toHaveTextContent('Initial summary')

    updateMockState({ sessionSummary: 'Updated summary with new content' })
    rerender(<SessionMetadataPanel />)
    expect(screen.getByTestId('session-summary')).toHaveTextContent('Updated summary with new content')
  })
})

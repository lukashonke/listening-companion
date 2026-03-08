import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SessionsPage } from './SessionsPage'

// Mock the auth module
vi.mock('@/lib/auth', () => ({
  apiFetch: vi.fn(),
}))

// Mock AppContext
const mockState = {
  transcript: [],
  toolLog: [],
  shortTermMemory: [],
  sessionName: 'New Session',
  isRecording: false,
  images: [],
}

vi.mock('@/context/AppContext', () => ({
  useAppContext: () => ({
    state: mockState,
    dispatchUI: vi.fn(),
  }),
}))

import { apiFetch } from '@/lib/auth'
const mockApiFetch = apiFetch as ReturnType<typeof vi.fn>

function renderPage() {
  return render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>
  )
}

const baseTime = 1700000000

function makeSessions(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: `sess_${i}`,
    name: `Session ${i}`,
    created_at: baseTime + i * 100,
    ended_at: null,
    config: '{}',
  }))
}

describe('SessionsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders sessions from paginated API response', async () => {
    const sessions = makeSessions(3)
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sessions, total: 3 }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Session 0')).toBeInTheDocument()
    })
    expect(screen.getByText('Session 1')).toBeInTheDocument()
    expect(screen.getByText('Session 2')).toBeInTheDocument()
  })

  it('shows pagination controls when there are multiple pages', async () => {
    const sessions = makeSessions(2)
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sessions, total: 50 }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Session 0')).toBeInTheDocument()
    })

    // Pagination controls should be visible
    expect(screen.getByText(/Page 1/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
  })

  it('disables Previous on first page', async () => {
    const sessions = makeSessions(2)
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sessions, total: 50 }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Session 0')).toBeInTheDocument()
    })

    const prevButton = screen.getByRole('button', { name: /previous/i })
    expect(prevButton).toBeDisabled()
  })

  it('disables Next on last page', async () => {
    const sessions = makeSessions(2)
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sessions, total: 2 }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Session 0')).toBeInTheDocument()
    })

    const nextButton = screen.getByRole('button', { name: /next/i })
    expect(nextButton).toBeDisabled()
  })

  it('clicking Next fetches next page', async () => {
    const page1 = makeSessions(2)
    const page2 = [{ id: 'sess_next_0', name: 'Next Page Session', created_at: baseTime + 500, ended_at: null, config: '{}' }]

    mockApiFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ sessions: page1, total: 42 }) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ sessions: page2, total: 42 }) })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Session 0')).toBeInTheDocument()
    })

    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    await waitFor(() => {
      expect(screen.getByText('Next Page Session')).toBeInTheDocument()
    })

    // Should have called apiFetch twice — second time with offset
    expect(mockApiFetch).toHaveBeenCalledTimes(2)
    const secondCallUrl = mockApiFetch.mock.calls[1][0] as string
    expect(secondCallUrl).toContain('offset=')
  })

  it('disables both buttons when only one page exists', async () => {
    const sessions = makeSessions(2)
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sessions, total: 2 }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Session 0')).toBeInTheDocument()
    })

    // When there's only one page, prev and next should both be disabled
    const prevButton = screen.getByRole('button', { name: /previous/i })
    const nextButton = screen.getByRole('button', { name: /next/i })
    expect(prevButton).toBeDisabled()
    expect(nextButton).toBeDisabled()
  })

  it('handles empty sessions list', async () => {
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sessions: [], total: 0 }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/no past sessions/i)).toBeInTheDocument()
    })
  })
})

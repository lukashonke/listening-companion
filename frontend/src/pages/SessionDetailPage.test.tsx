import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { SessionDetailPage } from './SessionDetailPage'

// Mock the auth module
vi.mock('@/lib/auth', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '@/lib/auth'

const mockApiFetch = apiFetch as ReturnType<typeof vi.fn>

function renderWithRouter(sessionId: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${sessionId}`]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

const mockSession = {
  id: 'sess_test123',
  name: 'Test Session',
  created_at: Date.now() / 1000 - 3600,
  ended_at: Date.now() / 1000,
  config: '{}',
  memory: [
    { id: 'mem_1', content: 'A memory entry', tags: ['tag1'], created_at: 1, updated_at: 1 },
  ],
}

const mockImages = [
  {
    id: 'img_001',
    session_id: 'sess_test123',
    filename: 'abc123.png',
    prompt: 'A beautiful sunset',
    style: 'realistic',
    provider: 'openai',
    created_at: Date.now() / 1000,
    url: '/api/images/abc123.png',
  },
  {
    id: 'img_002',
    session_id: 'sess_test123',
    filename: 'def456.png',
    prompt: 'A forest scene',
    style: 'cartoon',
    provider: 'gemini',
    created_at: Date.now() / 1000,
    url: '/api/images/def456.png',
  },
]

describe('SessionDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders session images tab with images from API', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (url.includes('/images')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockImages),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSession),
      })
    })

    renderWithRouter('sess_test123')

    // Wait for session to load
    await waitFor(() => {
      expect(screen.getByText('Test Session')).toBeInTheDocument()
    })

    // Click on Images tab
    const imagesTab = screen.getByRole('tab', { name: /images/i })
    expect(imagesTab).toBeInTheDocument()
    imagesTab.click()

    // Wait for images to load
    await waitFor(() => {
      expect(screen.getByText('A beautiful sunset')).toBeInTheDocument()
    })

    // Check both images are rendered
    expect(screen.getByText('A forest scene')).toBeInTheDocument()

    // Check image elements exist
    const images = screen.getAllByRole('img')
    expect(images.length).toBeGreaterThanOrEqual(2)
  })

  it('shows empty state when no images exist', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (url.includes('/images')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSession),
      })
    })

    renderWithRouter('sess_test123')

    // Wait for session to load
    await waitFor(() => {
      expect(screen.getByText('Test Session')).toBeInTheDocument()
    })

    // Click on Images tab
    const imagesTab = screen.getByRole('tab', { name: /images/i })
    imagesTab.click()

    // Should show empty state
    await waitFor(() => {
      expect(screen.getByText(/no images/i)).toBeInTheDocument()
    })
  })
})

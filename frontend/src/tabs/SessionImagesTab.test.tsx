import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SessionImagesTab } from './SessionImagesTab'
import type { AppState } from '@/store/types'
import { initialState } from '@/store/reducer'

// Mock the AppContext
vi.mock('@/context/AppContext', () => ({
  useAppContext: vi.fn(),
}))

import { useAppContext } from '@/context/AppContext'

const mockUseAppContext = useAppContext as ReturnType<typeof vi.fn>

function mockState(overrides: Partial<AppState> = {}) {
  mockUseAppContext.mockReturnValue({
    state: { ...initialState, ...overrides },
    dispatchWS: vi.fn(),
    dispatchUI: vi.fn(),
    sendJSON: vi.fn(),
    registerSendJSON: vi.fn(),
  })
}

describe('SessionImagesTab', () => {
  it('renders empty state when no images exist', () => {
    mockState({ images: [] })
    render(<SessionImagesTab />)
    expect(screen.getByText(/no images generated yet/i)).toBeInTheDocument()
  })

  it('renders a single image with /api/images/ URL', () => {
    mockState({
      images: [
        { url: '/api/images/abc123.png', prompt: 'A beautiful sunset', ts: 1000 },
      ],
    })
    render(<SessionImagesTab />)

    const img = screen.getByRole('img')
    expect(img).toHaveAttribute('src', '/api/images/abc123.png')
    expect(img).toHaveAttribute('alt', 'A beautiful sunset')
  })

  it('renders multiple images from persistent URLs', () => {
    mockState({
      images: [
        { url: '/api/images/img1.png', prompt: 'Sunset over ocean', ts: 1000 },
        { url: '/api/images/img2.png', prompt: 'Forest clearing', ts: 2000 },
        { url: '/api/images/img3.png', prompt: 'Mountain peak', ts: 3000 },
      ],
    })
    render(<SessionImagesTab />)

    const imgs = screen.getAllByRole('img')
    expect(imgs).toHaveLength(3)
    expect(imgs[0]).toHaveAttribute('src', '/api/images/img1.png')
    expect(imgs[1]).toHaveAttribute('src', '/api/images/img2.png')
    expect(imgs[2]).toHaveAttribute('src', '/api/images/img3.png')
  })

  it('displays prompt text for each image', () => {
    mockState({
      images: [
        { url: '/api/images/img1.png', prompt: 'Sunset over ocean', ts: 1000 },
        { url: '/api/images/img2.png', prompt: 'Forest clearing', ts: 2000 },
      ],
    })
    render(<SessionImagesTab />)

    expect(screen.getByText('Sunset over ocean')).toBeInTheDocument()
    expect(screen.getByText('Forest clearing')).toBeInTheDocument()
  })
})

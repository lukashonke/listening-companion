import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from './useWebSocket'

class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  readyState = MockWebSocket.CONNECTING
  onopen: ((e: Event) => void) | null = null
  onclose: ((e: CloseEvent) => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: ((e: Event) => void) | null = null
  send = vi.fn()
  close = vi.fn()
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }
  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }
  simulateClose() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  }
}

let mockWs: MockWebSocket
const MockWebSocketConstructor = Object.assign(
  vi.fn(function () {
    mockWs = new MockWebSocket()
    return mockWs
  }),
  { CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 }
) as unknown as typeof WebSocket

beforeEach(() => {
  vi.stubGlobal('WebSocket', MockWebSocketConstructor)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('useWebSocket', () => {
  it('connects on mount', () => {
    renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws', onEvent: vi.fn() }))
    expect(MockWebSocketConstructor).toHaveBeenCalledWith('ws://localhost:8000/ws')
  })

  it('calls onEvent with parsed JSON messages', () => {
    const onEvent = vi.fn()
    renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws', onEvent }))
    act(() => {
      mockWs.simulateOpen()
      mockWs.simulateMessage({ type: 'agent_start', ts: 1 })
    })
    expect(onEvent).toHaveBeenCalledWith({ type: 'agent_start', ts: 1 })
  })

  it('reconnects after close with backoff', () => {
    renderHook(() => useWebSocket({ url: 'ws://localhost:8000/ws', onEvent: vi.fn() }))
    act(() => {
      mockWs.simulateOpen()
      mockWs.simulateClose()
    })
    act(() => { vi.advanceTimersByTime(1100) })
    expect(MockWebSocketConstructor).toHaveBeenCalledTimes(2)
  })

  it('exposes sendBinary function', () => {
    const { result } = renderHook(() =>
      useWebSocket({ url: 'ws://localhost:8000/ws', onEvent: vi.fn() })
    )
    act(() => { mockWs.simulateOpen() })
    const buffer = new ArrayBuffer(8)
    act(() => { result.current.sendBinary(buffer) })
    expect(mockWs.send).toHaveBeenCalledWith(buffer)
  })

  it('does not send binary when socket is not open', () => {
    const { result } = renderHook(() =>
      useWebSocket({ url: 'ws://localhost:8000/ws', onEvent: vi.fn() })
    )
    // Socket is in CONNECTING state (not open)
    const buffer = new ArrayBuffer(8)
    act(() => { result.current.sendBinary(buffer) })
    expect(mockWs.send).not.toHaveBeenCalled()
  })
})

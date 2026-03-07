import { useEffect, useRef, useCallback } from 'react'
import type { WSEvent } from '@/store/types'

const BACKOFF_INITIAL_MS = 1000
const BACKOFF_MAX_MS = 30_000

interface UseWebSocketOptions {
  url: string
  onEvent: (event: WSEvent) => void
}

interface UseWebSocketReturn {
  sendBinary: (data: ArrayBuffer) => void
  sendJSON: (data: object) => void
}

export function useWebSocket({ url, onEvent }: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const backoffRef = useRef(BACKOFF_INITIAL_MS)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)
  // Keep a stable ref to the latest onEvent so we don't reconnect on every render
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      backoffRef.current = BACKOFF_INITIAL_MS
    }

    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data !== 'string') return
      try {
        const parsed = JSON.parse(event.data) as WSEvent
        onEventRef.current(parsed)
      } catch {
        // ignore malformed JSON
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      wsRef.current = null
      const delay = backoffRef.current
      backoffRef.current = Math.min(delay * 2, BACKOFF_MAX_MS)
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [url]) // url is intentionally the only dep; onEvent is via ref

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }, [])

  const sendJSON = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { sendBinary, sendJSON }
}

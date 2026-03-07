# Listening Companion Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete React + Vite + TypeScript + shadcn/ui frontend for the Listening Companion AI agent app with dark theme, collapsible sidebar navigation, live WebSocket-driven session view, and page-level routing.

**Architecture:** React Router v6 handles page-level navigation (sidebar items = routes). A single `useReducer` + Context manages all WebSocket-driven app state. Custom hooks (`useWebSocket`, `useAudioCapture`, `useTTSPlayer`) handle all real-time I/O.

**Tech Stack:** Vite 5, React 18, TypeScript 5, React Router v6, shadcn/ui (with Tailwind CSS v3), Vitest + Testing Library for unit tests.

---

### Task 1: Scaffold Vite + React + TypeScript project

**Files:**
- Create: `frontend/` (directory, via vite)

**Step 1: Scaffold the Vite project**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

Expected output: `frontend/` directory with `src/`, `index.html`, `vite.config.ts`, `tsconfig.json`.

**Step 2: Verify it starts**

```bash
cd frontend
npm run dev
```

Expected: Dev server running at `http://localhost:5173`. Ctrl+C to stop.

**Step 3: Clean up default boilerplate**

Delete: `frontend/src/App.css`, `frontend/src/assets/react.svg`, `frontend/public/vite.svg`

Replace `frontend/src/App.tsx` with minimal placeholder:
```tsx
export default function App() {
  return <div>Listening Companion</div>
}
```

Replace `frontend/src/index.css` with empty file (Tailwind will provide styles).

**Step 4: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/
git commit -m "feat: scaffold Vite + React + TypeScript frontend"
```

---

### Task 2: Install and configure shadcn/ui + Tailwind CSS

**Files:**
- Modify: `frontend/index.html` (add dark class to html element)
- Modify: `frontend/src/index.css` (Tailwind directives)
- Modify: `frontend/tailwind.config.ts`
- Create: `frontend/components.json` (shadcn config, auto-generated)

**Step 1: Install shadcn/ui**

```bash
cd frontend
npx shadcn@latest init
```

When prompted:
- Which style? → Default
- Which color? → Slate
- Use CSS variables? → Yes

This installs Tailwind, creates `tailwind.config.ts`, `components.json`, updates `src/index.css`.

**Step 2: Add dark class to html element**

In `frontend/index.html`, change:
```html
<html lang="en">
```
to:
```html
<html lang="en" class="dark">
```

**Step 3: Verify Tailwind dark theme**

Update `frontend/src/App.tsx` temporarily:
```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <h1 className="text-2xl font-bold">Listening Companion</h1>
    </div>
  )
}
```

Run `npm run dev` and verify dark background appears.

**Step 4: Install needed shadcn components upfront**

```bash
cd frontend
npx shadcn@latest add button badge card tabs toast tooltip separator scroll-area
```

**Step 5: Install React Router and other dependencies**

```bash
cd frontend
npm install react-router-dom
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event @vitejs/plugin-react jsdom
```

**Step 6: Configure Vitest**

Update `frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
```

Create `frontend/src/test/setup.ts`:
```ts
import '@testing-library/jest-dom'
```

Add to `frontend/package.json` scripts:
```json
"test": "vitest",
"test:run": "vitest run"
```

**Step 7: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/
git commit -m "feat: install shadcn/ui, Tailwind, React Router, Vitest"
```

---

### Task 3: Define all TypeScript types and state management

**Files:**
- Create: `frontend/src/store/types.ts`
- Create: `frontend/src/store/reducer.ts`
- Create: `frontend/src/context/AppContext.tsx`
- Create: `frontend/src/store/reducer.test.ts`

**Step 1: Write failing tests for reducer**

Create `frontend/src/store/reducer.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { appReducer, initialState } from './reducer'
import type { AppState, WSEvent } from './types'

describe('appReducer', () => {
  it('appends transcript chunks', () => {
    const event: WSEvent = {
      type: 'transcript_chunk',
      text: 'Hello world',
      speaker: 'A',
      ts: 1000,
    }
    const next = appReducer(initialState, event)
    expect(next.transcript).toHaveLength(1)
    expect(next.transcript[0].text).toBe('Hello world')
  })

  it('replaces short-term memory wholesale on memory_update', () => {
    const event: WSEvent = {
      type: 'memory_update',
      short_term: [{ id: 'mem_1', content: 'test', tags: ['a'], created_at: 1, updated_at: 1 }],
    }
    const next = appReducer(initialState, event)
    expect(next.shortTermMemory).toHaveLength(1)
    expect(next.shortTermMemory[0].id).toBe('mem_1')
  })

  it('keeps only last 100 tool log entries', () => {
    let state = initialState
    for (let i = 0; i < 102; i++) {
      const event: WSEvent = {
        type: 'tool_call',
        tool: 'test_tool',
        args: {},
        result: { id: `r${i}` },
        ts: i,
      }
      state = appReducer(state, event)
    }
    expect(state.toolLog).toHaveLength(100)
    expect(state.toolLog[99].ts).toBe(101)
  })

  it('sets isAgentThinking true on agent_start', () => {
    const event: WSEvent = { type: 'agent_start', ts: 1 }
    const next = appReducer(initialState, event)
    expect(next.isAgentThinking).toBe(true)
  })

  it('sets isAgentThinking false on agent_done', () => {
    const withThinking = { ...initialState, isAgentThinking: true }
    const event: WSEvent = { type: 'agent_done', ts: 2 }
    const next = appReducer(withThinking, event)
    expect(next.isAgentThinking).toBe(false)
  })

  it('updates sessionStatus on session_status', () => {
    const event: WSEvent = { type: 'session_status', state: 'listening' }
    const next = appReducer(initialState, event)
    expect(next.sessionStatus).toBe('listening')
  })

  it('appends images on image_generated', () => {
    const event: WSEvent = {
      type: 'image_generated',
      url: 'https://example.com/img.png',
      prompt: 'a cat',
      ts: 1,
    }
    const next = appReducer(initialState, event)
    expect(next.images).toHaveLength(1)
    expect(next.images[0].url).toBe('https://example.com/img.png')
  })

  it('sets error on error event', () => {
    const event: WSEvent = {
      type: 'error',
      code: 'stt_failed',
      message: 'STT disconnected',
      fatal: false,
    }
    const next = appReducer(initialState, event)
    expect(next.error).not.toBeNull()
    expect(next.error?.code).toBe('stt_failed')
  })
})
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
npm run test:run
```

Expected: FAIL — modules not found.

**Step 3: Write types**

Create `frontend/src/store/types.ts`:
```ts
export type SessionStatus = 'idle' | 'listening' | 'processing'

export interface TranscriptChunk {
  type: 'transcript_chunk'
  text: string
  speaker: string
  ts: number
}

export interface MemoryEntry {
  id: string
  content: string
  tags: string[]
  created_at: number
  updated_at: number
}

export interface ToolEvent {
  type: 'tool_call'
  tool: string
  args: Record<string, unknown>
  result: Record<string, unknown>
  ts: number
  error?: string
}

export interface GeneratedImage {
  url: string
  prompt: string
  ts: number
}

export interface AppError {
  code: string
  message: string
  fatal: boolean
}

export interface AppState {
  sessionStatus: SessionStatus
  transcript: TranscriptChunk[]
  shortTermMemory: MemoryEntry[]
  toolLog: ToolEvent[]
  images: GeneratedImage[]
  isAgentThinking: boolean
  error: AppError | null
  isRecording: boolean
  sessionName: string
}

// All WebSocket event types (server → client)
export type WSEvent =
  | { type: 'transcript_chunk'; text: string; speaker: string; ts: number }
  | { type: 'memory_update'; short_term: MemoryEntry[] }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown>; result: Record<string, unknown>; ts: number; error?: string }
  | { type: 'image_generated'; url: string; prompt: string; ts: number }
  | { type: 'agent_start'; ts: number }
  | { type: 'agent_done'; ts: number }
  | { type: 'session_status'; state: SessionStatus }
  | { type: 'tts_chunk'; audio_b64: string; text: string }
  | { type: 'error'; code: string; message: string; fatal: boolean }
```

**Step 4: Write reducer**

Create `frontend/src/store/reducer.ts`:
```ts
import type { AppState, WSEvent } from './types'

export const initialState: AppState = {
  sessionStatus: 'idle',
  transcript: [],
  shortTermMemory: [],
  toolLog: [],
  images: [],
  isAgentThinking: false,
  error: null,
  isRecording: false,
  sessionName: 'New Session',
}

const handlers: Partial<Record<WSEvent['type'], (state: AppState, event: WSEvent) => AppState>> = {
  transcript_chunk: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'transcript_chunk' }>
    return { ...s, transcript: [...s.transcript, ev] }
  },
  memory_update: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'memory_update' }>
    return { ...s, shortTermMemory: ev.short_term }
  },
  tool_call: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'tool_call' }>
    return { ...s, toolLog: [...s.toolLog.slice(-99), ev] }
  },
  image_generated: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'image_generated' }>
    return { ...s, images: [...s.images, ev] }
  },
  agent_start: (s) => ({ ...s, isAgentThinking: true }),
  agent_done: (s) => ({ ...s, isAgentThinking: false }),
  session_status: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'session_status' }>
    return { ...s, sessionStatus: ev.state }
  },
  error: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'error' }>
    return { ...s, error: { code: ev.code, message: ev.message, fatal: ev.fatal } }
  },
  tts_chunk: (s) => s, // handled by useTTSPlayer hook directly
}

export function appReducer(state: AppState, event: WSEvent): AppState {
  const handler = handlers[event.type]
  return handler ? handler(state, event) : state
}

// UI actions (not WS events)
export type UIAction =
  | { type: 'SET_RECORDING'; payload: boolean }
  | { type: 'SET_SESSION_NAME'; payload: string }
  | { type: 'CLEAR_ERROR' }
  | { type: 'RESET_SESSION' }

export function uiReducer(state: AppState, action: UIAction): AppState {
  switch (action.type) {
    case 'SET_RECORDING': return { ...state, isRecording: action.payload }
    case 'SET_SESSION_NAME': return { ...state, sessionName: action.payload }
    case 'CLEAR_ERROR': return { ...state, error: null }
    case 'RESET_SESSION': return { ...initialState, sessionName: state.sessionName }
    default: return state
  }
}
```

**Step 5: Run tests**

```bash
cd frontend
npm run test:run
```

Expected: All 8 tests PASS.

**Step 6: Create context**

Create `frontend/src/context/AppContext.tsx`:
```tsx
import { createContext, useContext, useReducer, useCallback, type ReactNode } from 'react'
import { appReducer, uiReducer, initialState } from '@/store/reducer'
import type { AppState, WSEvent } from '@/store/types'
import type { UIAction } from '@/store/reducer'

interface AppContextValue {
  state: AppState
  dispatchWS: (event: WSEvent) => void
  dispatchUI: (action: UIAction) => void
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(
    (s: AppState, action: WSEvent | UIAction) => {
      if ('type' in action && action.type.startsWith('SET_') ||
          action.type === 'CLEAR_ERROR' ||
          action.type === 'RESET_SESSION') {
        return uiReducer(s, action as UIAction)
      }
      return appReducer(s, action as WSEvent)
    },
    initialState
  )

  const dispatchWS = useCallback((event: WSEvent) => dispatch(event), [])
  const dispatchUI = useCallback((action: UIAction) => dispatch(action), [])

  return (
    <AppContext.Provider value={{ state, dispatchWS, dispatchUI }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used within AppProvider')
  return ctx
}
```

**Step 7: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/store/ frontend/src/context/ frontend/src/test/
git commit -m "feat: add AppState types, reducer, and context"
```

---

### Task 4: Build custom hooks

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/hooks/useAudioCapture.ts`
- Create: `frontend/src/hooks/useTTSPlayer.ts`
- Create: `frontend/public/audio-processor.worklet.js`
- Create: `frontend/src/hooks/useWebSocket.test.ts`

**Step 1: Write failing test for useWebSocket**

Create `frontend/src/hooks/useWebSocket.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from './useWebSocket'

// Mock WebSocket
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
const MockWebSocketConstructor = vi.fn(() => {
  mockWs = new MockWebSocket()
  return mockWs
})

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
    // First reconnect after 1000ms
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
})
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
npm run test:run -- src/hooks/useWebSocket.test.ts
```

Expected: FAIL — module not found.

**Step 3: Implement useWebSocket**

Create `frontend/src/hooks/useWebSocket.ts`:
```ts
import { useEffect, useRef, useCallback } from 'react'
import type { WSEvent } from '@/store/types'

const BACKOFF_INITIAL = 1000
const BACKOFF_MAX = 30000

interface UseWebSocketOptions {
  url: string
  onEvent: (event: WSEvent) => void
}

interface UseWebSocketReturn {
  sendBinary: (data: ArrayBuffer) => void
  sendJSON: (data: object) => void
  connected: boolean
}

export function useWebSocket({ url, onEvent }: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const backoffRef = useRef(BACKOFF_INITIAL)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const connectedRef = useRef(false)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      backoffRef.current = BACKOFF_INITIAL
      connectedRef.current = true
    }

    ws.onmessage = (event) => {
      if (typeof event.data !== 'string') return
      try {
        const parsed = JSON.parse(event.data) as WSEvent
        onEvent(parsed)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      connectedRef.current = false
      wsRef.current = null
      const delay = Math.min(backoffRef.current, BACKOFF_MAX)
      backoffRef.current = Math.min(backoffRef.current * 2, BACKOFF_MAX)
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [url, onEvent])

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

  return { sendBinary, sendJSON, connected: connectedRef.current }
}
```

**Step 4: Run tests**

```bash
cd frontend
npm run test:run -- src/hooks/useWebSocket.test.ts
```

Expected: All 4 tests PASS.

**Step 5: Implement useAudioCapture**

Create `frontend/src/hooks/useAudioCapture.ts`:
```ts
import { useRef, useCallback } from 'react'

interface UseAudioCaptureOptions {
  onAudioChunk: (buffer: ArrayBuffer) => void
  sampleRate?: number
}

export function useAudioCapture({ onAudioChunk, sampleRate = 16000 }: UseAudioCaptureOptions) {
  const contextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream

      const context = new AudioContext({ sampleRate })
      contextRef.current = context

      await context.audioWorklet.addModule('/audio-processor.worklet.js')

      const source = context.createMediaStreamSource(stream)
      const workletNode = new AudioWorkletNode(context, 'audio-processor')
      workletNodeRef.current = workletNode

      workletNode.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        onAudioChunk(e.data)
      }

      source.connect(workletNode)
      workletNode.connect(context.destination)
    } catch (err) {
      console.error('Audio capture failed:', err)
      throw err
    }
  }, [onAudioChunk, sampleRate])

  const stop = useCallback(() => {
    workletNodeRef.current?.disconnect()
    workletNodeRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    contextRef.current?.close()
    contextRef.current = null
  }, [])

  return { start, stop }
}
```

Create `frontend/public/audio-processor.worklet.js`:
```js
// AudioWorklet processor — runs in audio thread
// Captures PCM audio and sends 200ms chunks to main thread
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._buffer = []
    // 16kHz * 0.2s = 3200 samples per chunk
    this._chunkSize = Math.round(sampleRate * 0.2)
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input[0]) return true

    const samples = input[0] // Float32Array, mono
    for (let i = 0; i < samples.length; i++) {
      this._buffer.push(samples[i])
    }

    while (this._buffer.length >= this._chunkSize) {
      const chunk = this._buffer.splice(0, this._chunkSize)
      // Convert Float32 to Int16 PCM
      const pcm = new Int16Array(chunk.length)
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]))
        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
      }
      this.port.postMessage(pcm.buffer, [pcm.buffer])
    }

    return true
  }
}

registerProcessor('audio-processor', AudioProcessor)
```

**Step 6: Implement useTTSPlayer**

Create `frontend/src/hooks/useTTSPlayer.ts`:
```ts
import { useRef, useCallback } from 'react'

export function useTTSPlayer() {
  const contextRef = useRef<AudioContext | null>(null)
  const queueRef = useRef<AudioBuffer[]>([])
  const playingRef = useRef(false)

  function getContext(): AudioContext {
    if (!contextRef.current) {
      contextRef.current = new AudioContext()
    }
    return contextRef.current
  }

  function playNext() {
    if (queueRef.current.length === 0) {
      playingRef.current = false
      return
    }
    playingRef.current = true
    const ctx = getContext()
    const buffer = queueRef.current.shift()!
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.onended = playNext
    source.start()
  }

  const enqueue = useCallback(async (audio_b64: string) => {
    try {
      const ctx = getContext()
      const binary = atob(audio_b64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
      const audioBuffer = await ctx.decodeAudioData(bytes.buffer)
      queueRef.current.push(audioBuffer)
      if (!playingRef.current) playNext()
    } catch (err) {
      console.error('TTS decode failed:', err)
    }
  }, [])

  return { enqueue }
}
```

**Step 7: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/hooks/ frontend/public/
git commit -m "feat: add useWebSocket, useAudioCapture, useTTSPlayer hooks"
```

---

### Task 5: Build layout shell — Sidebar

**Files:**
- Create: `frontend/src/components/sidebar/Sidebar.tsx`
- Create: `frontend/src/components/sidebar/NavItem.tsx`

**Step 1: Implement Sidebar**

Create `frontend/src/components/sidebar/NavItem.tsx`:
```tsx
import { cn } from '@/lib/utils'
import { NavLink } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

interface NavItemProps {
  to: string
  icon: LucideIcon
  label: string
  collapsed: boolean
}

export function NavItem({ to, icon: Icon, label, collapsed }: NavItemProps) {
  const item = (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          'hover:bg-accent hover:text-accent-foreground',
          isActive
            ? 'bg-accent text-accent-foreground'
            : 'text-muted-foreground',
          collapsed && 'justify-center px-2'
        )
      }
    >
      <Icon className="h-5 w-5 shrink-0" />
      {!collapsed && <span>{label}</span>}
    </NavLink>
  )

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{item}</TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
    )
  }
  return item
}
```

Create `frontend/src/components/sidebar/Sidebar.tsx`:
```tsx
import { useState } from 'react'
import { History, Brain, ImageIcon, Settings, ChevronLeft, ChevronRight } from 'lucide-react'
import { NavItem } from './NavItem'
import { cn } from '@/lib/utils'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'

const navItems = [
  { to: '/sessions', icon: History, label: 'Sessions' },
  { to: '/memory', icon: Brain, label: 'Memory' },
  { to: '/images', icon: ImageIcon, label: 'Images' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'hidden md:flex flex-col border-r border-border bg-card transition-all duration-200',
          collapsed ? 'w-14' : 'w-52'
        )}
      >
        {/* Logo / brand */}
        <div className={cn('flex items-center h-14 px-3 gap-2', collapsed && 'justify-center px-0')}>
          {!collapsed && (
            <span className="font-semibold text-sm text-foreground truncate">
              Listening Companion
            </span>
          )}
        </div>

        <Separator />

        {/* Nav items */}
        <nav className="flex-1 flex flex-col gap-1 p-2">
          {navItems.map((item) => (
            <NavItem key={item.to} {...item} collapsed={collapsed} />
          ))}
        </nav>

        <Separator />

        {/* Collapse toggle */}
        <div className="p-2 flex justify-end">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  )
}
```

**Step 2: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/components/sidebar/
git commit -m "feat: add collapsible sidebar with icon-based nav"
```

---

### Task 6: Build layout shell — TopBar

**Files:**
- Create: `frontend/src/components/topbar/TopBar.tsx`
- Create: `frontend/src/components/topbar/MicIndicator.tsx`
- Create: `frontend/src/components/topbar/RecordButton.tsx`

**Step 1: Implement MicIndicator**

Create `frontend/src/components/topbar/MicIndicator.tsx`:
```tsx
import { cn } from '@/lib/utils'

interface MicIndicatorProps {
  isRecording: boolean
  isConnecting?: boolean
}

export function MicIndicator({ isRecording, isConnecting }: MicIndicatorProps) {
  if (isConnecting) {
    return (
      <div className="flex items-center gap-1.5">
        <div className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
        <span className="text-xs text-muted-foreground">Reconnecting…</span>
      </div>
    )
  }

  if (isRecording) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
        </span>
        <span className="text-xs text-muted-foreground">Recording</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5">
      <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
      <span className="text-xs text-muted-foreground">Idle</span>
    </div>
  )
}
```

Create `frontend/src/components/topbar/RecordButton.tsx`:
```tsx
import { Mic, MicOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface RecordButtonProps {
  isRecording: boolean
  isLoading?: boolean
  onClick: () => void
}

export function RecordButton({ isRecording, isLoading, onClick }: RecordButtonProps) {
  return (
    <Button
      variant={isRecording ? 'destructive' : 'default'}
      size="sm"
      onClick={onClick}
      disabled={isLoading}
      className="gap-2"
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : isRecording ? (
        <MicOff className="h-4 w-4" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
      {isRecording ? 'Stop' : 'Start'}
    </Button>
  )
}
```

Create `frontend/src/components/topbar/TopBar.tsx`:
```tsx
import { Plus, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RecordButton } from './RecordButton'
import { MicIndicator } from './MicIndicator'
import { useAppContext } from '@/context/AppContext'
import { useCallback, useState } from 'react'
import { useAudioCapture } from '@/hooks/useAudioCapture'

interface TopBarProps {
  onSendBinary: (data: ArrayBuffer) => void
}

export function TopBar({ onSendBinary }: TopBarProps) {
  const { state, dispatchUI } = useAppContext()
  const [isStarting, setIsStarting] = useState(false)

  const { start: startAudio, stop: stopAudio } = useAudioCapture({
    onAudioChunk: onSendBinary,
  })

  const handleToggleRecord = useCallback(async () => {
    if (state.isRecording) {
      stopAudio()
      dispatchUI({ type: 'SET_RECORDING', payload: false })
    } else {
      setIsStarting(true)
      try {
        await startAudio()
        dispatchUI({ type: 'SET_RECORDING', payload: true })
      } catch {
        // mic permission denied or not available
      } finally {
        setIsStarting(false)
      }
    }
  }, [state.isRecording, startAudio, stopAudio, dispatchUI])

  const handleNewSession = useCallback(() => {
    stopAudio()
    dispatchUI({ type: 'RESET_SESSION' })
  }, [stopAudio, dispatchUI])

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-4 gap-3">
      <RecordButton
        isRecording={state.isRecording}
        isLoading={isStarting}
        onClick={handleToggleRecord}
      />

      <Button variant="outline" size="sm" onClick={handleNewSession} className="gap-2">
        <Plus className="h-4 w-4" />
        <span className="hidden sm:inline">New Session</span>
      </Button>

      {/* Session name */}
      <span className="hidden md:block text-sm font-medium text-foreground truncate flex-1 max-w-xs">
        {state.sessionName}
      </span>

      <div className="flex-1" />

      {/* Agent thinking indicator */}
      {state.isAgentThinking && (
        <Badge variant="secondary" className="gap-1.5 animate-pulse">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
          Agent thinking…
        </Badge>
      )}

      <MicIndicator isRecording={state.isRecording} />

      <NavLink to="/settings">
        <Button variant="ghost" size="icon" aria-label="Settings">
          <Settings className="h-4 w-4" />
        </Button>
      </NavLink>
    </header>
  )
}
```

**Step 2: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/components/topbar/
git commit -m "feat: add TopBar with record button, mic indicator, session controls"
```

---

### Task 7: Build AppLayout and route scaffolding

**Files:**
- Create: `frontend/src/app/AppLayout.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/components/sidebar/MobileNav.tsx`

**Step 1: Implement AppLayout**

Create `frontend/src/app/AppLayout.tsx`:
```tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { TopBar } from '@/components/topbar/TopBar'
import { MobileNav } from '@/components/sidebar/MobileNav'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useTTSPlayer } from '@/hooks/useTTSPlayer'
import { useAppContext } from '@/context/AppContext'
import { useCallback, useRef } from 'react'
import type { WSEvent } from '@/store/types'
import { ErrorBanner } from '@/components/ErrorBanner'
import { Toaster } from '@/components/ui/toaster'
import { useToast } from '@/hooks/use-toast'

const WS_URL = 'ws://localhost:8000/ws'

export function AppLayout() {
  const { dispatchWS, dispatchUI, state } = useAppContext()
  const { enqueue: enqueueTTS } = useTTSPlayer()
  const { toast } = useToast()
  const sendBinaryRef = useRef<(data: ArrayBuffer) => void>(() => {})

  const handleEvent = useCallback((event: WSEvent) => {
    if (event.type === 'tts_chunk') {
      enqueueTTS(event.audio_b64)
      return
    }
    if (event.type === 'error' && !event.fatal) {
      toast({ title: event.code, description: event.message, variant: 'destructive' })
    }
    dispatchWS(event)
  }, [dispatchWS, enqueueTTS, toast])

  const { sendBinary, sendJSON } = useWebSocket({ url: WS_URL, onEvent: handleEvent })

  // keep ref stable so TopBar can pass binary frames
  sendBinaryRef.current = sendBinary

  const handleSendBinary = useCallback((data: ArrayBuffer) => {
    sendBinaryRef.current(data)
  }, [])

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar onSendBinary={handleSendBinary} />
        {state.error?.fatal && (
          <ErrorBanner
            message={state.error.message}
            onRestart={() => {
              dispatchUI({ type: 'RESET_SESSION' })
              sendJSON({ type: 'session_end' })
            }}
          />
        )}
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
        <MobileNav />
      </div>
      <Toaster />
    </div>
  )
}
```

Create `frontend/src/components/sidebar/MobileNav.tsx`:
```tsx
import { NavLink } from 'react-router-dom'
import { History, Brain, ImageIcon, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/sessions', icon: History, label: 'Sessions' },
  { to: '/memory', icon: Brain, label: 'Memory' },
  { to: '/images', icon: ImageIcon, label: 'Images' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function MobileNav() {
  return (
    <nav className="md:hidden border-t border-border bg-card flex">
      {navItems.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              'flex-1 flex flex-col items-center py-2 gap-0.5 text-xs transition-colors',
              isActive
                ? 'text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )
          }
        >
          <Icon className="h-5 w-5" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
```

Create `frontend/src/components/ErrorBanner.tsx`:
```tsx
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ErrorBannerProps {
  message: string
  onRestart: () => void
}

export function ErrorBanner({ message, onRestart }: ErrorBannerProps) {
  return (
    <div className="bg-destructive/15 border-b border-destructive/30 px-4 py-2 flex items-center gap-3">
      <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
      <span className="text-sm text-destructive flex-1">{message}</span>
      <Button variant="destructive" size="sm" onClick={onRestart}>
        Restart Session
      </Button>
    </div>
  )
}
```

**Step 2: Implement App router**

Create `frontend/src/app/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider } from '@/context/AppContext'
import { AppLayout } from './AppLayout'
import { SessionsPage } from '@/pages/SessionsPage'
import { ActiveSessionPage } from '@/pages/ActiveSessionPage'
import { MemoryPage } from '@/pages/MemoryPage'
import { ImagesPage } from '@/pages/ImagesPage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Navigate to="/sessions" replace />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/sessions/current" element={<ActiveSessionPage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/images" element={<ImagesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  )
}
```

Update `frontend/src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/index.css'
import App from '@/app/App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

**Step 3: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/app/ frontend/src/components/ frontend/src/main.tsx
git commit -m "feat: add AppLayout with router, sidebar, mobile nav, error banner"
```

---

### Task 8: Build the 3 active session tabs

**Files:**
- Create: `frontend/src/tabs/TranscriptTab.tsx`
- Create: `frontend/src/tabs/AgentLogTab.tsx`
- Create: `frontend/src/tabs/MemoryTab.tsx`

**Step 1: Implement TranscriptTab**

Create `frontend/src/tabs/TranscriptTab.tsx`:
```tsx
import { useEffect, useRef } from 'react'
import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { formatTime } from '@/lib/formatTime'

export function TranscriptTab() {
  const { state } = useAppContext()
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new chunks
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [state.transcript.length])

  if (state.transcript.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        {state.isRecording ? 'Listening…' : 'Start recording to see transcript'}
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1 h-full px-4 py-3">
      <div className="space-y-2 max-w-3xl mx-auto">
        {state.transcript.map((chunk, i) => (
          <div key={i} className="flex gap-3 items-start">
            <span className="text-xs text-muted-foreground mt-0.5 shrink-0 font-mono w-16">
              {formatTime(chunk.ts)}
            </span>
            {chunk.speaker && (
              <Badge variant="outline" className="shrink-0 text-xs h-5 mt-0.5">
                {chunk.speaker}
              </Badge>
            )}
            <p className="text-sm text-foreground leading-relaxed">{chunk.text}</p>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}
```

Create `frontend/src/lib/formatTime.ts`:
```ts
export function formatTime(ts: number): string {
  const d = new Date(ts * 1000)
  const h = d.getHours().toString().padStart(2, '0')
  const m = d.getMinutes().toString().padStart(2, '0')
  const s = d.getSeconds().toString().padStart(2, '0')
  return `${h}:${m}:${s}`
}
```

**Step 2: Implement AgentLogTab**

Create `frontend/src/tabs/AgentLogTab.tsx`:
```tsx
import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useEffect, useRef } from 'react'
import { formatTime } from '@/lib/formatTime'
import { Loader2 } from 'lucide-react'

export function AgentLogTab() {
  const { state } = useAppContext()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [state.toolLog.length])

  return (
    <ScrollArea className="flex-1 h-full px-4 py-3">
      <div className="space-y-2 max-w-3xl mx-auto">
        {state.isAgentThinking && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-1">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Agent is processing…
          </div>
        )}
        {state.toolLog.length === 0 && !state.isAgentThinking && (
          <div className="flex items-center justify-center h-24 text-muted-foreground text-sm">
            No agent activity yet
          </div>
        )}
        {state.toolLog.map((event, i) => (
          <Card key={i} className="bg-card/50 border-border/50">
            <CardContent className="p-3 space-y-1.5">
              <div className="flex items-center gap-2">
                <Badge variant={event.error ? 'destructive' : 'secondary'} className="text-xs">
                  {event.tool}
                </Badge>
                <span className="text-xs text-muted-foreground font-mono ml-auto">
                  {formatTime(event.ts)}
                </span>
              </div>
              {Object.keys(event.args).length > 0 && (
                <pre className="text-xs text-muted-foreground bg-muted/50 rounded p-2 overflow-x-auto">
                  {JSON.stringify(event.args, null, 2)}
                </pre>
              )}
              {event.error && (
                <p className="text-xs text-destructive">Error: {event.error}</p>
              )}
            </CardContent>
          </Card>
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}
```

**Step 3: Implement MemoryTab**

Create `frontend/src/tabs/MemoryTab.tsx`:
```tsx
import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Brain } from 'lucide-react'

export function MemoryTab() {
  const { state } = useAppContext()

  if (state.shortTermMemory.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
        <Brain className="h-8 w-8 opacity-30" />
        <span className="text-sm">No memory entries yet</span>
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1 h-full px-4 py-3">
      <div className="grid gap-2 max-w-3xl mx-auto sm:grid-cols-2">
        {state.shortTermMemory.map((entry) => (
          <Card key={entry.id} className="bg-card/50 border-border/50">
            <CardContent className="p-3 space-y-2">
              <p className="text-sm text-foreground leading-relaxed">{entry.content}</p>
              {entry.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {entry.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs h-4 px-1.5">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </ScrollArea>
  )
}
```

**Step 4: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/tabs/ frontend/src/lib/
git commit -m "feat: add TranscriptTab, AgentLogTab, MemoryTab"
```

---

### Task 9: Build all pages

**Files:**
- Create: `frontend/src/pages/SessionsPage.tsx`
- Create: `frontend/src/pages/ActiveSessionPage.tsx`
- Create: `frontend/src/pages/MemoryPage.tsx`
- Create: `frontend/src/pages/ImagesPage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`

**Step 1: Implement ActiveSessionPage (most complex)**

Create `frontend/src/pages/ActiveSessionPage.tsx`:
```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TranscriptTab } from '@/tabs/TranscriptTab'
import { AgentLogTab } from '@/tabs/AgentLogTab'
import { MemoryTab } from '@/tabs/MemoryTab'
import { useAppContext } from '@/context/AppContext'
import { FileText, Wrench, Brain } from 'lucide-react'

export function ActiveSessionPage() {
  const { state } = useAppContext()

  return (
    <Tabs defaultValue="transcript" className="flex flex-col h-full">
      <div className="border-b border-border px-4">
        <TabsList className="bg-transparent h-10 p-0 gap-1">
          <TabsTrigger
            value="transcript"
            className="gap-1.5 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
          >
            <FileText className="h-3.5 w-3.5" />
            Transcript
            {state.transcript.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">
                ({state.transcript.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="agent-log"
            className="gap-1.5 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
          >
            <Wrench className="h-3.5 w-3.5" />
            Agent Log
            {state.toolLog.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">
                ({state.toolLog.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="memory"
            className="gap-1.5 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
          >
            <Brain className="h-3.5 w-3.5" />
            Memory
            {state.shortTermMemory.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">
                ({state.shortTermMemory.length})
              </span>
            )}
          </TabsTrigger>
        </TabsList>
      </div>
      <TabsContent value="transcript" className="flex-1 mt-0 overflow-hidden">
        <TranscriptTab />
      </TabsContent>
      <TabsContent value="agent-log" className="flex-1 mt-0 overflow-hidden">
        <AgentLogTab />
      </TabsContent>
      <TabsContent value="memory" className="flex-1 mt-0 overflow-hidden">
        <MemoryTab />
      </TabsContent>
    </Tabs>
  )
}
```

**Step 2: Implement SessionsPage**

Create `frontend/src/pages/SessionsPage.tsx`:
```tsx
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Plus, Mic } from 'lucide-react'
import { useAppContext } from '@/context/AppContext'

export function SessionsPage() {
  const navigate = useNavigate()
  const { state } = useAppContext()

  const hasActivity = state.transcript.length > 0 || state.toolLog.length > 0

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Sessions</h1>
          <Button size="sm" onClick={() => navigate('/sessions/current')} className="gap-2">
            <Plus className="h-4 w-4" />
            New Session
          </Button>
        </div>

        {hasActivity ? (
          <Card
            className="cursor-pointer hover:bg-accent/50 transition-colors border-border/70"
            onClick={() => navigate('/sessions/current')}
          >
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Mic className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm">{state.sessionName}</p>
                <p className="text-xs text-muted-foreground">
                  {state.transcript.length} transcript chunks · {state.shortTermMemory.length} memory entries
                </p>
              </div>
              <div className={`h-2 w-2 rounded-full ${state.isRecording ? 'bg-red-500 animate-pulse' : 'bg-muted-foreground/30'}`} />
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
            <Mic className="h-12 w-12 text-muted-foreground/30" />
            <div>
              <p className="text-muted-foreground">No sessions yet</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Click "New Session" or "Start" in the top bar to begin recording
              </p>
            </div>
            <Button onClick={() => navigate('/sessions/current')} className="gap-2">
              <Plus className="h-4 w-4" />
              Start Session
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 3: Implement MemoryPage**

Create `frontend/src/pages/MemoryPage.tsx`:
```tsx
import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Brain, Clock } from 'lucide-react'
import { formatTime } from '@/lib/formatTime'

export function MemoryPage() {
  const { state } = useAppContext()

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border px-6 py-4 flex items-center gap-2">
        <Brain className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Memory</h1>
        <Badge variant="secondary" className="ml-auto">
          {state.shortTermMemory.length} entries
        </Badge>
      </div>

      {state.shortTermMemory.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
          <Brain className="h-10 w-10 opacity-20" />
          <p className="text-sm">No short-term memory entries yet</p>
          <p className="text-xs opacity-70">The agent will populate this as it listens</p>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <div className="p-6 grid gap-3 max-w-4xl mx-auto sm:grid-cols-2 lg:grid-cols-3">
            {state.shortTermMemory.map((entry) => (
              <Card key={entry.id} className="bg-card border-border/70">
                <CardHeader className="pb-2 pt-3 px-4">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {formatTime(entry.updated_at)}
                    <span className="ml-auto font-mono text-muted-foreground/50">{entry.id}</span>
                  </div>
                </CardHeader>
                <CardContent className="px-4 pb-3 space-y-2">
                  <p className="text-sm text-foreground leading-relaxed">{entry.content}</p>
                  {entry.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {entry.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs h-4 px-1.5">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
```

**Step 4: Implement ImagesPage**

Create `frontend/src/pages/ImagesPage.tsx`:
```tsx
import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { ImageIcon } from 'lucide-react'
import { formatTime } from '@/lib/formatTime'

export function ImagesPage() {
  const { state } = useAppContext()

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border px-6 py-4 flex items-center gap-2">
        <ImageIcon className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Images</h1>
        <Badge variant="secondary" className="ml-auto">
          {state.images.length}
        </Badge>
      </div>

      {state.images.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
          <ImageIcon className="h-10 w-10 opacity-20" />
          <p className="text-sm">No images generated yet</p>
          <p className="text-xs opacity-70">The agent will generate images during sessions</p>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <div className="p-6 grid gap-4 max-w-5xl mx-auto sm:grid-cols-2 lg:grid-cols-3">
            {state.images.map((img, i) => (
              <div key={i} className="group relative rounded-lg overflow-hidden border border-border/70 bg-card">
                <img
                  src={img.url}
                  alt={img.prompt}
                  className="w-full aspect-square object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                  <p className="text-xs text-white/90 leading-relaxed line-clamp-3">{img.prompt}</p>
                  <p className="text-xs text-white/50 mt-1">{formatTime(img.ts)}</p>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
```

**Step 5: Implement SettingsPage**

Create `frontend/src/pages/SettingsPage.tsx`:
```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Settings } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export function SettingsPage() {
  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Settings</h1>
        </div>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-sm">WebSocket Connection</CardTitle>
            <CardDescription>Backend connection settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Endpoint</span>
              <code className="text-xs bg-muted px-2 py-0.5 rounded font-mono">
                ws://localhost:8000/ws
              </code>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-sm">Audio</CardTitle>
            <CardDescription>Capture settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Sample Rate</span>
              <Badge variant="secondary">16 kHz</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Format</span>
              <Badge variant="secondary">PCM 16-bit mono</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Chunk size</span>
              <Badge variant="secondary">200ms</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-sm">About</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-1">
            <p>Listening Companion — AI-powered real-time conversation assistant</p>
            <p className="text-xs opacity-70">Backend: FastAPI + Pydantic AI + Claude</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

**Step 6: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/pages/
git commit -m "feat: add all pages (Sessions, ActiveSession, Memory, Images, Settings)"
```

---

### Task 10: Wire up, fix TypeScript, verify build

**Step 1: Install lucide-react (icons)**

```bash
cd frontend
npm install lucide-react
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend
npm run build
```

Fix any TypeScript errors that appear. Common issues:
- Missing `path` import in vite.config.ts: `import path from 'path'` and `npm install -D @types/node`
- Strict null checks in hooks
- Missing shadcn component hooks (use-toast)

**Step 3: Run all tests**

```bash
cd frontend
npm run test:run
```

Expected: All tests pass.

**Step 4: Smoke-test in browser**

```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` and verify:
- Dark theme renders
- Sidebar shows icons (Sessions, Memory, Images, Settings)
- Sidebar collapses/expands with toggle
- Each nav item navigates to the correct page
- Mobile nav appears on narrow viewport
- TopBar shows Start/Stop button

**Step 5: Commit final state**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/
git commit -m "feat: complete frontend — all pages, hooks, state management, dark theme"
```

---

### Task 11: Save MEMORY.md

**Step 1: Write memory file**

Create `/home/lukashonke/.claude/projects/-home-lukashonke-projects-listening-companion-claude-code/memory/MEMORY.md` with key project facts.

**Step 2: Final cleanup commit and notification**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
openclaw system event --text 'Claude Code done: frontend built' --mode now
```

---

## Summary

Total tasks: 11
Commits: ~10 atomic commits
Tests: reducer tests (8), useWebSocket tests (4)
Pages: Sessions, ActiveSession (3 tabs), Memory, Images, Settings
Hooks: useWebSocket, useAudioCapture, useTTSPlayer
Components: Sidebar (collapsible), TopBar, MobileNav, ErrorBanner, all tabs

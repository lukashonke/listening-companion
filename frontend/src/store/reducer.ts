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

type Handler = (state: AppState, event: WSEvent) => AppState

const handlers: Partial<Record<WSEvent['type'], Handler>> = {
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

// UI-only actions (not WS events)
export type UIAction =
  | { type: 'SET_RECORDING'; payload: boolean }
  | { type: 'SET_SESSION_NAME'; payload: string }
  | { type: 'CLEAR_ERROR' }
  | { type: 'RESET_SESSION' }

export function uiReducer(state: AppState, action: UIAction): AppState {
  switch (action.type) {
    case 'SET_RECORDING':
      return { ...state, isRecording: action.payload }
    case 'SET_SESSION_NAME':
      return { ...state, sessionName: action.payload }
    case 'CLEAR_ERROR':
      return { ...state, error: null }
    case 'RESET_SESSION':
      return { ...initialState, sessionName: state.sessionName }
    default:
      return state
  }
}

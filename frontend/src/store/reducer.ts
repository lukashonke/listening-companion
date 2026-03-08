import type { AppState, GeneratedImage, SessionConfig, WSEvent } from './types'

const DEFAULT_CONFIG: SessionConfig = {
  voice_id: 'P1bg08DkjqiVEzOn76yG',
  agent_interval_s: 30,
  image_provider: 'gemini',
  image_model: 'imagen-4.0-fast-generate-001',
  image_prompt_theme: '',
  tools: [],
  speaker_diarization: false,
  audio_chunk_ms: 1000,
  stt_language: 'cs',
  tts_model: 'eleven_v3',
  tts_language: 'cs',
  agent_model: 'gpt-5.3-chat-latest',
  custom_system_prompt: '',
  theme: '',
  model_provider: 'openai',
  reasoning_effort: 'medium',
  auto_naming_enabled: true,
  auto_naming_first_trigger: 5,
  auto_naming_repeat_interval: 10,
  auto_summarization_enabled: true,
  auto_summarization_interval: 300,
  auto_summarization_max_transcript_length: 50000,
  agent_trigger_mode: 'transcript',
}

export const initialState: AppState = {
  sessionStatus: 'idle',
  transcript: [],
  shortTermMemory: [],
  toolLog: [],
  images: [],
  logs: [],
  isAgentThinking: false,
  error: null,
  isRecording: false,
  sessionName: 'New Session',
  sessionNameSource: 'default',
  sessionSummary: '',
  config: DEFAULT_CONFIG,
  resumeSessionId: null,
  currentSpeech: null,
}

export { DEFAULT_CONFIG }

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
  agent_done: (s) => ({ ...s, isAgentThinking: false, currentSpeech: null }),
  session_status: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'session_status' }>
    return { ...s, sessionStatus: ev.state }
  },
  error: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'error' }>
    return { ...s, error: { code: ev.code, message: ev.message, fatal: ev.fatal } }
  },
  tts_chunk: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'tts_chunk' }>
    // Store spoken text for live stage display; audio handled by useTTSPlayer
    return { ...s, currentSpeech: { text: ev.text, ts: Date.now() } }
  },
  log: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'log' }>
    return { ...s, logs: [...s.logs.slice(-999), { level: ev.level, message: ev.message, ts: ev.ts }] }
  },
  session_name_update: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'session_name_update' }>
    return { ...s, sessionName: ev.name, sessionNameSource: ev.name_source }
  },
  session_summary_update: (s, e) => {
    const ev = e as Extract<WSEvent, { type: 'session_summary_update' }>
    return { ...s, sessionSummary: ev.summary }
  },
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
  | { type: 'CLEAR_LOGS' }
  | { type: 'RESET_SESSION' }
  | { type: 'SET_CONFIG'; payload: Partial<SessionConfig> }
  | { type: 'SET_RESUME_SESSION_ID'; payload: string | null }
  | { type: 'SET_IMAGES'; payload: GeneratedImage[] }

export function uiReducer(state: AppState, action: UIAction): AppState {
  switch (action.type) {
    case 'SET_RECORDING':
      return { ...state, isRecording: action.payload }
    case 'SET_SESSION_NAME':
      return { ...state, sessionName: action.payload }
    case 'CLEAR_ERROR':
      return { ...state, error: null }
    case 'CLEAR_LOGS':
      return { ...state, logs: [] }
    case 'RESET_SESSION':
      return { ...initialState, config: state.config, sessionName: state.sessionName, resumeSessionId: null }
    case 'SET_CONFIG':
      return { ...state, config: { ...state.config, ...action.payload } }
    case 'SET_RESUME_SESSION_ID':
      return { ...state, resumeSessionId: action.payload }
    case 'SET_IMAGES':
      return { ...state, images: action.payload }
    default:
      return state
  }
}

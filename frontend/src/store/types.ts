export type SessionStatus = 'idle' | 'listening' | 'processing'

export interface SessionConfig {
  voice_id: string;
  agent_interval_s: number;
  image_provider: string;
  image_model: string;
  image_prompt_theme: string;
  tools: string[];
  speaker_diarization: boolean;
  audio_chunk_ms: number;
  stt_language: string;
  tts_model: string;
  tts_language: string;
  agent_model: string;
  // R5
  custom_system_prompt: string;
  // R6
  theme: string;
  // R8
  model_provider: string;
  reasoning_effort: string;
  // Background AI features
  auto_naming_enabled: boolean;
  auto_naming_first_trigger: number;
  auto_naming_repeat_interval: number;
  auto_summarization_enabled: boolean;
  auto_summarization_interval: number;
  auto_summarization_max_transcript_length: number;
}

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
  result: Record<string, unknown> | string | null
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

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

export interface LogEntry {
  level: LogLevel
  message: string
  ts: number
}

export interface TTSSpeech {
  text: string
  ts: number
}

export interface AppState {
  sessionStatus: SessionStatus
  transcript: TranscriptChunk[]
  shortTermMemory: MemoryEntry[]
  toolLog: ToolEvent[]
  images: GeneratedImage[]
  logs: LogEntry[]
  isAgentThinking: boolean
  error: AppError | null
  isRecording: boolean
  sessionName: string
  config: SessionConfig
  resumeSessionId: string | null
  /** Currently spoken TTS text (for live stage display) */
  currentSpeech: TTSSpeech | null
}

// All WebSocket event types (server → client)
export type WSEvent =
  | { type: 'transcript_chunk'; text: string; speaker: string; ts: number }
  | { type: 'memory_update'; short_term: MemoryEntry[] }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown>; result: Record<string, unknown> | string | null; ts: number; error?: string }
  | { type: 'image_generated'; url: string; prompt: string; ts: number }
  | { type: 'agent_start'; ts: number }
  | { type: 'agent_done'; ts: number }
  | { type: 'session_status'; state: SessionStatus }
  | { type: 'tts_chunk'; audio_b64: string; text: string }
  | { type: 'error'; code: string; message: string; fatal: boolean }
  | { type: 'log'; level: LogLevel; message: string; ts: number }
  | { type: 'session_name_update'; name: string; name_source: string }

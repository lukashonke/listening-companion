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

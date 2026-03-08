import { describe, it, expect } from 'vitest'
import { appReducer, uiReducer, initialState } from './reducer'
import type { UIAction } from './reducer'
import type { WSEvent } from './types'

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

  it('returns same state for unknown event type', () => {
    const event = { type: 'unknown_event' } as unknown as WSEvent
    const next = appReducer(initialState, event)
    expect(next).toBe(initialState)
  })

  it('appends images with /api/images/ persistent URLs', () => {
    const event: WSEvent = {
      type: 'image_generated',
      url: '/api/images/abc123.png',
      prompt: 'a forest scene',
      ts: 1000,
    }
    const next = appReducer(initialState, event)
    expect(next.images).toHaveLength(1)
    expect(next.images[0].url).toBe('/api/images/abc123.png')
    expect(next.images[0].prompt).toBe('a forest scene')
  })

  it('accumulates multiple images from image_generated events', () => {
    let state = initialState
    const images = [
      { type: 'image_generated' as const, url: '/api/images/img1.png', prompt: 'sunset', ts: 1 },
      { type: 'image_generated' as const, url: '/api/images/img2.png', prompt: 'forest', ts: 2 },
      { type: 'image_generated' as const, url: '/api/images/img3.png', prompt: 'ocean', ts: 3 },
    ]
    for (const event of images) {
      state = appReducer(state, event)
    }
    expect(state.images).toHaveLength(3)
    expect(state.images[0].url).toBe('/api/images/img1.png')
    expect(state.images[1].url).toBe('/api/images/img2.png')
    expect(state.images[2].url).toBe('/api/images/img3.png')
  })

  it('updates sessionName on session_name_update event', () => {
    const event: WSEvent = {
      type: 'session_name_update',
      name: 'Meeting Notes Discussion',
      name_source: 'auto',
    }
    const next = appReducer(initialState, event)
    expect(next.sessionName).toBe('Meeting Notes Discussion')
  })

  it('session_name_update replaces existing session name', () => {
    const stateWithName = { ...initialState, sessionName: 'Old Name' }
    const event: WSEvent = {
      type: 'session_name_update',
      name: 'New Auto Name',
      name_source: 'auto',
    }
    const next = appReducer(stateWithName, event)
    expect(next.sessionName).toBe('New Auto Name')
  })

  it('session_name_update stores name_source in state', () => {
    const event: WSEvent = {
      type: 'session_name_update',
      name: 'Auto Named Session',
      name_source: 'auto',
    }
    const next = appReducer(initialState, event)
    expect(next.sessionNameSource).toBe('auto')
  })

  it('session_name_update tracks user name_source', () => {
    const event: WSEvent = {
      type: 'session_name_update',
      name: 'User Named Session',
      name_source: 'user',
    }
    const next = appReducer(initialState, event)
    expect(next.sessionNameSource).toBe('user')
  })

  it('updates sessionSummary on session_summary_update event', () => {
    const event: WSEvent = {
      type: 'session_summary_update',
      summary: 'A discussion about music theory and chord progressions.',
    }
    const next = appReducer(initialState, event)
    expect(next.sessionSummary).toBe('A discussion about music theory and chord progressions.')
  })

  it('session_summary_update replaces existing summary', () => {
    const stateWithSummary = { ...initialState, sessionSummary: 'Old summary' }
    const event: WSEvent = {
      type: 'session_summary_update',
      summary: 'Updated comprehensive summary with new content.',
    }
    const next = appReducer(stateWithSummary, event)
    expect(next.sessionSummary).toBe('Updated comprehensive summary with new content.')
  })

  it('session_summary_update clears summary with empty string', () => {
    const stateWithSummary = { ...initialState, sessionSummary: 'Some summary' }
    const event: WSEvent = {
      type: 'session_summary_update',
      summary: '',
    }
    const next = appReducer(stateWithSummary, event)
    expect(next.sessionSummary).toBe('')
  })
})

describe('DEFAULT_CONFIG background AI fields', () => {
  it('has auto-naming defaults', () => {
    expect(initialState.config.auto_naming_enabled).toBe(true)
    expect(initialState.config.auto_naming_first_trigger).toBe(5)
    expect(initialState.config.auto_naming_repeat_interval).toBe(10)
  })

  it('has auto-summarization defaults', () => {
    expect(initialState.config.auto_summarization_enabled).toBe(true)
    expect(initialState.config.auto_summarization_interval).toBe(300)
    expect(initialState.config.auto_summarization_max_transcript_length).toBe(50000)
  })

  it('has agent_trigger_mode default as transcript', () => {
    expect(initialState.config.agent_trigger_mode).toBe('transcript')
  })

  it('has empty sessionSummary in initial state', () => {
    expect(initialState.sessionSummary).toBe('')
  })

  it('has default sessionNameSource in initial state', () => {
    expect(initialState.sessionNameSource).toBe('default')
  })
})

describe('uiReducer', () => {
  it('sets images via SET_IMAGES action', () => {
    const action: UIAction = {
      type: 'SET_IMAGES',
      payload: [
        { url: '/api/images/abc123.png', prompt: 'a sunset', ts: 1000 },
        { url: '/api/images/def456.png', prompt: 'a forest', ts: 2000 },
      ],
    }
    const next = uiReducer(initialState, action)
    expect(next.images).toHaveLength(2)
    expect(next.images[0].url).toBe('/api/images/abc123.png')
    expect(next.images[1].url).toBe('/api/images/def456.png')
  })

  it('SET_IMAGES replaces existing images', () => {
    const stateWithImages = {
      ...initialState,
      images: [{ url: '/api/images/old.png', prompt: 'old', ts: 500 }],
    }
    const action: UIAction = {
      type: 'SET_IMAGES',
      payload: [{ url: '/api/images/new.png', prompt: 'new', ts: 1000 }],
    }
    const next = uiReducer(stateWithImages, action)
    expect(next.images).toHaveLength(1)
    expect(next.images[0].url).toBe('/api/images/new.png')
  })

  it('RESET_SESSION clears images', () => {
    const stateWithImages = {
      ...initialState,
      images: [{ url: '/api/images/abc.png', prompt: 'test', ts: 1000 }],
    }
    const action: UIAction = { type: 'RESET_SESSION' }
    const next = uiReducer(stateWithImages, action)
    expect(next.images).toHaveLength(0)
  })

  it('RESET_SESSION clears sessionSummary', () => {
    const stateWithSummary = {
      ...initialState,
      sessionSummary: 'Some summary from previous session',
    }
    const action: UIAction = { type: 'RESET_SESSION' }
    const next = uiReducer(stateWithSummary, action)
    expect(next.sessionSummary).toBe('')
  })

  it('RESET_SESSION resets sessionNameSource to default', () => {
    const stateWithNameSource = {
      ...initialState,
      sessionNameSource: 'auto',
    }
    const action: UIAction = { type: 'RESET_SESSION' }
    const next = uiReducer(stateWithNameSource, action)
    expect(next.sessionNameSource).toBe('default')
  })
})

/**
 * Cross-area integration tests for the frontend store.
 *
 * Verifies that:
 * - Auto-naming WS events update the right panel state
 * - Auto-summarization WS events update the right panel state
 * - Config settings include all background AI feature fields
 * - Image events use persistent URLs
 * - RESET_SESSION clears summary and resets name source
 */
import { describe, it, expect } from 'vitest'
import { appReducer, uiReducer, initialState, DEFAULT_CONFIG } from './reducer'
import type { WSEvent, AppState } from './types'

describe('Cross-area integration', () => {
  describe('auto-naming updates right panel state', () => {
    it('session_name_update updates sessionName and sessionNameSource', () => {
      const state = { ...initialState }
      const event: WSEvent = {
        type: 'session_name_update',
        name: 'Music Theory Discussion',
        name_source: 'auto',
      }
      const next = appReducer(state, event)
      expect(next.sessionName).toBe('Music Theory Discussion')
      expect(next.sessionNameSource).toBe('auto')
    })

    it('subsequent name updates reflect re-evaluation', () => {
      const state: AppState = {
        ...initialState,
        sessionName: 'Music Theory Discussion',
        sessionNameSource: 'auto',
      }
      const event: WSEvent = {
        type: 'session_name_update',
        name: 'Advanced Music Theory',
        name_source: 'auto',
      }
      const next = appReducer(state, event)
      expect(next.sessionName).toBe('Advanced Music Theory')
      expect(next.sessionNameSource).toBe('auto')
    })
  })

  describe('auto-summarization updates right panel state', () => {
    it('session_summary_update updates sessionSummary', () => {
      const state = { ...initialState }
      const event: WSEvent = {
        type: 'session_summary_update',
        summary: 'A great discussion about music theory covering scales and chords.',
      }
      const next = appReducer(state, event)
      expect(next.sessionSummary).toBe(
        'A great discussion about music theory covering scales and chords.'
      )
    })

    it('subsequent summary updates replace previous summary', () => {
      const state: AppState = {
        ...initialState,
        sessionSummary: 'Initial summary about music.',
      }
      const event: WSEvent = {
        type: 'session_summary_update',
        summary: 'Extended summary covering music theory, including scales, chords, and progressions.',
      }
      const next = appReducer(state, event)
      expect(next.sessionSummary).toBe(
        'Extended summary covering music theory, including scales, chords, and progressions.'
      )
    })
  })

  describe('config includes all background AI settings', () => {
    it('DEFAULT_CONFIG has all auto-naming fields', () => {
      expect(DEFAULT_CONFIG.auto_naming_enabled).toBe(true)
      expect(DEFAULT_CONFIG.auto_naming_first_trigger).toBe(5)
      expect(DEFAULT_CONFIG.auto_naming_repeat_interval).toBe(10)
    })

    it('DEFAULT_CONFIG has all auto-summarization fields', () => {
      expect(DEFAULT_CONFIG.auto_summarization_enabled).toBe(true)
      expect(DEFAULT_CONFIG.auto_summarization_interval).toBe(300)
      expect(DEFAULT_CONFIG.auto_summarization_max_transcript_length).toBe(50000)
    })

    it('SET_CONFIG can override auto-summarization interval', () => {
      const state = { ...initialState }
      const next = uiReducer(state, {
        type: 'SET_CONFIG',
        payload: { auto_summarization_interval: 60 },
      })
      expect(next.config.auto_summarization_interval).toBe(60)
      // Other config values remain
      expect(next.config.auto_naming_enabled).toBe(true)
    })
  })

  describe('image events use persistent URLs', () => {
    it('image_generated event adds image with persistent URL', () => {
      const state = { ...initialState }
      const event: WSEvent = {
        type: 'image_generated',
        url: '/api/images/abc123.png',
        prompt: 'A beautiful sunset',
        ts: Date.now(),
      }
      const next = appReducer(state, event)
      expect(next.images).toHaveLength(1)
      expect(next.images[0].url).toBe('/api/images/abc123.png')
      expect(next.images[0].prompt).toBe('A beautiful sunset')
    })

    it('multiple images accumulate in state', () => {
      let state = { ...initialState }
      const events: WSEvent[] = [
        { type: 'image_generated', url: '/api/images/img1.png', prompt: 'Image 1', ts: 1000 },
        { type: 'image_generated', url: '/api/images/img2.png', prompt: 'Image 2', ts: 2000 },
        { type: 'image_generated', url: '/api/images/img3.png', prompt: 'Image 3', ts: 3000 },
      ]
      for (const event of events) {
        state = appReducer(state, event)
      }
      expect(state.images).toHaveLength(3)
      expect(state.images.map(i => i.url)).toEqual([
        '/api/images/img1.png',
        '/api/images/img2.png',
        '/api/images/img3.png',
      ])
    })

    it('SET_IMAGES replaces all images (session resume)', () => {
      const state: AppState = {
        ...initialState,
        images: [{ url: '/api/images/old.png', prompt: 'old', ts: 1 }],
      }
      const next = uiReducer(state, {
        type: 'SET_IMAGES',
        payload: [
          { url: '/api/images/resumed1.png', prompt: 'Resumed 1', ts: 100 },
          { url: '/api/images/resumed2.png', prompt: 'Resumed 2', ts: 200 },
        ],
      })
      expect(next.images).toHaveLength(2)
      expect(next.images[0].url).toBe('/api/images/resumed1.png')
    })
  })

  describe('RESET_SESSION clears session-specific state', () => {
    it('resets summary and name source but keeps config', () => {
      const state: AppState = {
        ...initialState,
        sessionName: 'Auto Named Session',
        sessionNameSource: 'auto',
        sessionSummary: 'A detailed summary.',
        config: { ...DEFAULT_CONFIG, auto_summarization_interval: 60 },
        images: [{ url: '/api/images/test.png', prompt: 'test', ts: 1 }],
      }
      const next = uiReducer(state, { type: 'RESET_SESSION' })

      // Summary should be cleared
      expect(next.sessionSummary).toBe('')
      // Name source should reset to default
      expect(next.sessionNameSource).toBe('default')
      // Config should be preserved
      expect(next.config.auto_summarization_interval).toBe(60)
      // Images should be cleared
      expect(next.images).toHaveLength(0)
      // Session name is preserved (from old state)
      expect(next.sessionName).toBe('Auto Named Session')
    })
  })
})

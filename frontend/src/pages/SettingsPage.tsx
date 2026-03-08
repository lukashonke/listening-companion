import { useEffect, useState } from 'react'
import { useAppContext } from '@/context/AppContext'
import { apiFetch } from '@/lib/auth'

const AGENT_INTERVALS = [10, 30, 60, 120]

const IMAGE_PROVIDERS = [
  { value: 'placeholder', label: 'Placeholder (no API key)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Google Gemini' },
]

const OPENAI_IMAGE_MODELS_FALLBACK = [
  { value: 'gpt-image-1', label: 'gpt-image-1' },
  { value: 'gpt-image-1-mini', label: 'gpt-image-1-mini' },
  { value: 'dall-e-3', label: 'dall-e-3' },
]

const GEMINI_IMAGE_MODELS_FALLBACK = [
  { value: 'gemini-2.5-flash-image', label: 'gemini-2.5-flash-image' },
  { value: 'gemini-3-pro-image-preview', label: 'gemini-3-pro-image-preview' },
  { value: 'nano-banana-pro-preview', label: 'nano-banana-pro-preview' },
  { value: 'imagen-4.0-generate-001', label: 'imagen-4.0-generate-001' },
]

const AUDIO_CHUNK_OPTIONS = [
  { value: 200, label: '200ms (low latency)' },
  { value: 500, label: '500ms' },
  { value: 1000, label: '1000ms (1s)' },
]

const STT_LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'cs', label: 'Czech' },
  { value: 'de', label: 'German' },
  { value: 'fr', label: 'French' },
  { value: 'es', label: 'Spanish' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'zh', label: 'Chinese' },
]

const TTS_LANGUAGES = [
  { value: 'cs', label: 'Czech (default)' },
  { value: 'en', label: 'English' },
  { value: 'de', label: 'German' },
  { value: 'fr', label: 'French' },
  { value: 'es', label: 'Spanish' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'zh', label: 'Chinese' },
  { value: 'pl', label: 'Polish' },
  { value: 'sk', label: 'Slovak' },
]

const TTS_MODELS = [
  { value: 'eleven_v3', label: 'Eleven v3 (latest)' },
  { value: 'eleven_turbo_v2_5', label: 'Eleven Turbo v2.5 (fast)' },
  { value: 'eleven_flash_v2_5', label: 'Eleven Flash v2.5 (fastest)' },
]

const ANTHROPIC_MODELS = [
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (default)' },
  { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
  { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
]

// Fallback list used while loading or if the API call fails
const OPENAI_MODELS_FALLBACK = [
  { value: 'gpt-4o', label: 'gpt-4o' },
  { value: 'gpt-4o-mini', label: 'gpt-4o-mini' },
  { value: 'gpt-4.1', label: 'gpt-4.1' },
  { value: 'gpt-4.1-mini', label: 'gpt-4.1-mini' },
  { value: 'gpt-4.1-nano', label: 'gpt-4.1-nano' },
  { value: 'o1', label: 'o1' },
  { value: 'o1-pro', label: 'o1-pro' },
  { value: 'o3', label: 'o3' },
  { value: 'o3-mini', label: 'o3-mini' },
  { value: 'o3-pro', label: 'o3-pro' },
  { value: 'o4-mini', label: 'o4-mini' },
]

const GEMINI_MODELS_FALLBACK = [
  { value: 'gemini-2.5-flash', label: 'gemini-2.5-flash' },
  { value: 'gemini-2.5-pro', label: 'gemini-2.5-pro' },
  { value: 'gemini-2.0-flash', label: 'gemini-2.0-flash' },
  { value: 'gemini-2.0-flash-lite', label: 'gemini-2.0-flash-lite' },
]

const REASONING_EFFORTS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium (default)' },
  { value: 'high', label: 'High' },
]

const OPENAI_REASONING_MODELS = new Set(['o1', 'o3', 'o4-mini', 'o4-mini-high', 'o3-pro'])

function isReasoningModel(model: string) {
  return OPENAI_REASONING_MODELS.has(model) || model.startsWith('o1') || model.startsWith('o3') || model.startsWith('o4')
}

export function SettingsPage() {
  const { state, dispatchUI, sendJSON } = useAppContext()
  const { config, isRecording } = state

  const [openaiModels, setOpenaiModels] = useState<{ value: string; label: string }[] | null>(null)
  const [loadingOpenaiModels, setLoadingOpenaiModels] = useState(false)
  const [geminiModels, setGeminiModels] = useState<{ value: string; label: string }[] | null>(null)
  const [loadingGeminiModels, setLoadingGeminiModels] = useState(false)
  const [openaiImageModels, setOpenaiImageModels] = useState<{ value: string; label: string }[] | null>(null)
  const [geminiImageModels, setGeminiImageModels] = useState<{ value: string; label: string }[] | null>(null)
  const [voices, setVoices] = useState<{ id: string; name: string; category: string }[]>([])
  const [loadingVoices, setLoadingVoices] = useState(false)

  useEffect(() => {
    if (config.model_provider !== 'openai') return
    setLoadingOpenaiModels(true)
    apiFetch('/api/models/openai')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data.models) && data.models.length > 0) {
          setOpenaiModels(data.models.map((id: string) => ({ value: id, label: id })))
        }
      })
      .catch(() => { /* fall back to hardcoded list */ })
      .finally(() => setLoadingOpenaiModels(false))
  }, [config.model_provider])

  useEffect(() => {
    if (config.model_provider !== 'google') return
    setLoadingGeminiModels(true)
    apiFetch('/api/models/gemini')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data.models) && data.models.length > 0) {
          setGeminiModels(data.models.map((id: string) => ({ value: id, label: id })))
        }
      })
      .catch(() => { /* fall back to hardcoded list */ })
      .finally(() => setLoadingGeminiModels(false))
  }, [config.model_provider])

  useEffect(() => {
    setLoadingVoices(true)
    apiFetch('/api/voices/elevenlabs')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data.voices) && data.voices.length > 0) {
          setVoices(data.voices)
        }
      })
      .catch(() => { /* keep empty — user can still type voice_id */ })
      .finally(() => setLoadingVoices(false))
  }, [])

  useEffect(() => {
    apiFetch('/api/models/openai-image')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data.models) && data.models.length > 0) {
          setOpenaiImageModels(data.models.map((id: string) => ({ value: id, label: id })))
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    apiFetch('/api/models/gemini-image')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data.models) && data.models.length > 0) {
          setGeminiImageModels(data.models.map((id: string) => ({ value: id, label: id })))
        }
      })
      .catch(() => {})
  }, [])

  const updateConfig = (patch: Partial<typeof config>) => {
    dispatchUI({ type: 'SET_CONFIG', payload: patch })
    if (isRecording) {
      sendJSON({ type: 'config_update', config: patch })
    }
  }

  const agentModels =
    config.model_provider === 'openai' ? (openaiModels ?? OPENAI_MODELS_FALLBACK) :
    config.model_provider === 'google' ? (geminiModels ?? GEMINI_MODELS_FALLBACK) :
    ANTHROPIC_MODELS
  const loadingAgentModels = loadingOpenaiModels || loadingGeminiModels
  const defaultAgentModel =
    config.model_provider === 'openai' ? 'gpt-4o' :
    config.model_provider === 'google' ? 'gemini-2.5-flash' :
    'claude-sonnet-4-6'
  const showReasoningEffort = config.model_provider === 'openai' && isReasoningModel(config.agent_model)

  const imageModels =
    config.image_provider === 'openai' ? (openaiImageModels ?? OPENAI_IMAGE_MODELS_FALLBACK) :
    config.image_provider === 'gemini' ? (geminiImageModels ?? GEMINI_IMAGE_MODELS_FALLBACK) :
    []
  const defaultImageModel =
    config.image_provider === 'openai' ? 'gpt-image-1' :
    config.image_provider === 'gemini' ? 'gemini-2.5-flash-image' :
    ''

  return (
    <div className="h-full overflow-y-auto">
    <div className="p-6 max-w-lg space-y-8">
      <h1 className="text-xl font-semibold">Settings</h1>

      {/* Audio */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Audio</h2>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Audio Chunk Interval</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.audio_chunk_ms}
            onChange={e => updateConfig({ audio_chunk_ms: Number(e.target.value) })}
          >
            {AUDIO_CHUNK_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">How often audio is sent to the backend (affects latency vs. overhead tradeoff)</p>
        </div>

        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium">Speaker Diarization</p>
            <p className="text-xs text-muted-foreground">Label speakers A, B, C in transcript</p>
          </div>
          <button
            type="button"
            onClick={() => updateConfig({ speaker_diarization: !config.speaker_diarization })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
              config.speaker_diarization ? 'bg-primary' : 'bg-muted'
            }`}
            aria-pressed={config.speaker_diarization}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              config.speaker_diarization ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>
      </section>

      {/* Speech-to-Text */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Speech-to-Text</h2>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">STT Language</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.stt_language}
            onChange={e => updateConfig({ stt_language: e.target.value })}
          >
            {STT_LANGUAGES.map(l => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">Language spoken in the recording</p>
        </div>
      </section>

      {/* Text-to-Speech */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Text-to-Speech</h2>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Voice (ElevenLabs)</label>
          {voices.length > 0 ? (
            <select
              className="w-full px-3 py-2 rounded-md border bg-background text-sm"
              value={config.voice_id}
              onChange={e => updateConfig({ voice_id: e.target.value })}
            >
              {voices.map(v => (
                <option key={v.id} value={v.id}>{v.name}{v.category ? ` (${v.category})` : ''}</option>
              ))}
            </select>
          ) : (
            <input
              className="w-full px-3 py-2 rounded-md border bg-background text-sm"
              value={config.voice_id}
              onChange={e => updateConfig({ voice_id: e.target.value })}
              placeholder={loadingVoices ? 'Loading voices…' : 'JBFqnCBsd6RMkjVDRZzb'}
              disabled={loadingVoices}
            />
          )}
          <p className="text-xs text-muted-foreground">ElevenLabs voice for spoken responses</p>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">TTS Language</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.tts_language}
            onChange={e => updateConfig({ tts_language: e.target.value })}
          >
            {TTS_LANGUAGES.map(l => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">Language for spoken responses</p>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">TTS Model</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.tts_model}
            onChange={e => updateConfig({ tts_model: e.target.value })}
          >
            {TTS_MODELS.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
      </section>

      {/* Agent */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Agent</h2>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Model Provider</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.model_provider}
            onChange={e => {
              const provider = e.target.value
              const model = provider === 'openai' ? 'gpt-4o' : provider === 'google' ? 'gemini-2.5-flash' : 'claude-sonnet-4-6'
              updateConfig({ model_provider: provider, agent_model: model })
            }}
          >
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="openai">OpenAI</option>
            <option value="google">Google Gemini</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Agent Model</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.agent_model || defaultAgentModel}
            onChange={e => updateConfig({ agent_model: e.target.value })}
            disabled={loadingAgentModels}
          >
            {loadingAgentModels
              ? <option>Loading models…</option>
              : agentModels.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))
            }
          </select>
          {config.model_provider === 'openai' && openaiModels && (
            <p className="text-xs text-muted-foreground">{openaiModels.length} models fetched from OpenAI API</p>
          )}
          {config.model_provider === 'google' && geminiModels && (
            <p className="text-xs text-muted-foreground">{geminiModels.length} models fetched from Google API</p>
          )}
        </div>

        {showReasoningEffort && (
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Reasoning Effort</label>
            <select
              className="w-full px-3 py-2 rounded-md border bg-background text-sm"
              value={config.reasoning_effort}
              onChange={e => updateConfig({ reasoning_effort: e.target.value })}
            >
              {REASONING_EFFORTS.map(r => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">Higher effort produces better results but uses more tokens and is slower</p>
          </div>
        )}

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Trigger Mode</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.agent_trigger_mode}
            onChange={e => updateConfig({ agent_trigger_mode: e.target.value })}
          >
            <option value="transcript">On transcript</option>
            <option value="timer">On timer</option>
          </select>
          <p className="text-xs text-muted-foreground">
            {config.agent_trigger_mode === 'transcript'
              ? 'Agent runs after each committed transcript chunk (with cooldown)'
              : 'Agent runs on a fixed timer interval'}
          </p>
        </div>

        {config.agent_trigger_mode === 'timer' && (
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Agent Interval</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.agent_interval_s}
            onChange={e => updateConfig({ agent_interval_s: Number(e.target.value) })}
          >
            {AGENT_INTERVALS.map(s => (
              <option key={s} value={s}>{s} seconds</option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">How often the AI agent reviews the transcript</p>
        </div>
        )}

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Custom System Prompt</label>
          <textarea
            className="w-full px-3 py-2 rounded-md border bg-background text-sm resize-none"
            rows={4}
            value={config.custom_system_prompt}
            onChange={e => updateConfig({ custom_system_prompt: e.target.value })}
            placeholder="Additional instructions appended to the agent's system prompt…"
          />
          <p className="text-xs text-muted-foreground">Appended to the built-in prompt. Leave blank to use defaults.</p>
        </div>
      </section>

      {/* Images */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Images</h2>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Image Provider</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.image_provider}
            onChange={e => updateConfig({ image_provider: e.target.value, image_model: '' })}
          >
            {IMAGE_PROVIDERS.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        {config.image_provider !== 'placeholder' && imageModels.length > 0 && (
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Image Model</label>
            <select
              className="w-full px-3 py-2 rounded-md border bg-background text-sm"
              value={config.image_model || defaultImageModel}
              onChange={e => updateConfig({ image_model: e.target.value })}
            >
              {imageModels.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
        )}

        {config.image_provider !== 'placeholder' && (
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Image Style / Theme</label>
            <textarea
              className="w-full px-3 py-2 rounded-md border bg-background text-sm min-h-[60px] resize-y"
              value={config.image_prompt_theme}
              onChange={e => updateConfig({ image_prompt_theme: e.target.value })}
              placeholder="e.g. D&D fantasy art style, watercolor, dark and moody, anime style..."
              rows={2}
            />
            <p className="text-xs text-muted-foreground">Style instructions added to every image generation prompt</p>
          </div>
        )}
      </section>

      {/* Background AI Features */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Background AI Features</h2>

        {/* Auto-Naming */}
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-medium">Auto-Naming</p>
              <p className="text-xs text-muted-foreground">Automatically name sessions based on transcript content</p>
            </div>
            <button
              type="button"
              onClick={() => updateConfig({ auto_naming_enabled: !config.auto_naming_enabled })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                config.auto_naming_enabled ? 'bg-primary' : 'bg-muted'
              }`}
              aria-pressed={config.auto_naming_enabled}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                config.auto_naming_enabled ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          </div>

          {config.auto_naming_enabled && (
            <>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">First Trigger (chunks)</label>
                <input
                  type="number"
                  className="w-full px-3 py-2 rounded-md border bg-background text-sm"
                  value={config.auto_naming_first_trigger}
                  onChange={e => updateConfig({ auto_naming_first_trigger: Math.max(1, Number(e.target.value)) })}
                  min={1}
                />
                <p className="text-xs text-muted-foreground">Number of transcript chunks before first auto-naming attempt</p>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Repeat Interval (chunks)</label>
                <input
                  type="number"
                  className="w-full px-3 py-2 rounded-md border bg-background text-sm"
                  value={config.auto_naming_repeat_interval}
                  onChange={e => updateConfig({ auto_naming_repeat_interval: Math.max(1, Number(e.target.value)) })}
                  min={1}
                />
                <p className="text-xs text-muted-foreground">Number of additional chunks between name re-evaluations</p>
              </div>
            </>
          )}
        </div>

        {/* Auto-Summarization */}
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-medium">Auto-Summarization</p>
              <p className="text-xs text-muted-foreground">Automatically generate session summaries at regular intervals</p>
            </div>
            <button
              type="button"
              onClick={() => updateConfig({ auto_summarization_enabled: !config.auto_summarization_enabled })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                config.auto_summarization_enabled ? 'bg-primary' : 'bg-muted'
              }`}
              aria-pressed={config.auto_summarization_enabled}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                config.auto_summarization_enabled ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          </div>

          {config.auto_summarization_enabled && (
            <>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Summarization Interval (seconds)</label>
                <input
                  type="number"
                  className="w-full px-3 py-2 rounded-md border bg-background text-sm"
                  value={config.auto_summarization_interval}
                  onChange={e => updateConfig({ auto_summarization_interval: Math.max(30, Number(e.target.value)) })}
                  min={30}
                />
                <p className="text-xs text-muted-foreground">How often to generate an updated summary</p>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Max Transcript Length (chars)</label>
                <input
                  type="number"
                  className="w-full px-3 py-2 rounded-md border bg-background text-sm"
                  value={config.auto_summarization_max_transcript_length}
                  onChange={e => updateConfig({ auto_summarization_max_transcript_length: Math.max(1000, Number(e.target.value)) })}
                  min={1000}
                />
                <p className="text-xs text-muted-foreground">Maximum transcript characters sent to the LLM for summarization</p>
              </div>
            </>
          )}
        </div>
      </section>

      {isRecording && (
        <p className="text-xs text-amber-500">
          Changes are applied live to the current session.
        </p>
      )}
    </div>
    </div>
  )
}

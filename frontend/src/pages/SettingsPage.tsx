import { useAppContext } from '@/context/AppContext'

const AGENT_INTERVALS = [10, 30, 60, 120]

const IMAGE_PROVIDERS = [
  { value: 'placeholder', label: 'Placeholder (no API key)' },
  { value: 'fal', label: 'fal.ai Flux' },
  { value: 'openai', label: 'OpenAI gpt-image-1' },
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

const TTS_MODELS = [
  { value: 'eleven_v3', label: 'Eleven v3 (latest)' },
  { value: 'eleven_turbo_v2_5', label: 'Eleven Turbo v2.5 (fast)' },
  { value: 'eleven_flash_v2_5', label: 'Eleven Flash v2.5 (fastest)' },
]

const AGENT_MODELS = [
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (default)' },
  { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
  { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 (fast)' },
]

export function SettingsPage() {
  const { state, dispatchUI, sendJSON } = useAppContext()
  const { config, isRecording } = state

  const updateConfig = (patch: Partial<typeof config>) => {
    dispatchUI({ type: 'SET_CONFIG', payload: patch })
    if (isRecording) {
      sendJSON({ type: 'config_update', config: patch })
    }
  }

  return (
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
          <label className="text-sm font-medium">Voice ID (ElevenLabs)</label>
          <input
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.voice_id}
            onChange={e => updateConfig({ voice_id: e.target.value })}
            placeholder="JBFqnCBsd6RMkjVDRZzb"
          />
          <p className="text-xs text-muted-foreground">ElevenLabs voice ID for spoken responses</p>
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
          <label className="text-sm font-medium">Agent Model</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.agent_model}
            onChange={e => updateConfig({ agent_model: e.target.value })}
          >
            {AGENT_MODELS.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

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
      </section>

      {/* Images */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Images</h2>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Image Provider</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.image_provider}
            onChange={e => updateConfig({ image_provider: e.target.value })}
          >
            {IMAGE_PROVIDERS.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
      </section>

      {isRecording && (
        <p className="text-xs text-amber-500">
          Changes are applied live to the current session.
        </p>
      )}
    </div>
  )
}

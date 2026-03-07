import { useAppContext } from '@/context/AppContext'

const AGENT_INTERVALS = [10, 30, 60, 120]
const IMAGE_PROVIDERS = [
  { value: 'placeholder', label: 'Placeholder (no API key)' },
  { value: 'fal', label: 'fal.ai Flux' },
  { value: 'openai', label: 'OpenAI gpt-image-1' },
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
    <div className="p-6 max-w-lg space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <div className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Voice ID (ElevenLabs)</label>
          <input
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.voice_id}
            onChange={e => updateConfig({ voice_id: e.target.value })}
            placeholder="JBFqnCBsd6RMkjVDRZzb"
          />
          <p className="text-xs text-muted-foreground">ElevenLabs voice ID for TTS spoken responses</p>
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
      </div>

      {isRecording && (
        <p className="text-xs text-amber-500">
          Changes are applied live to the current session.
        </p>
      )}
    </div>
  )
}

import { useCallback, useState } from 'react'
import { Plus, Settings } from 'lucide-react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RecordButton } from './RecordButton'
import { MicIndicator } from './MicIndicator'
import { useAppContext } from '@/context/AppContext'
import { useAudioCapture } from '@/hooks/useAudioCapture'

interface TopBarProps {
  onSendBinary: (data: ArrayBuffer) => void
  isConnected: boolean
  onSessionEnd: () => void
  onSessionStart: () => void
}

export function TopBar({ onSendBinary, isConnected, onSessionEnd, onSessionStart }: TopBarProps) {
  const { state, dispatchUI } = useAppContext()
  const [isStarting, setIsStarting] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const { start: startAudio, stop: stopAudio } = useAudioCapture({
    onAudioChunk: onSendBinary,
    chunkIntervalMs: state.config.audio_chunk_ms,
  })

  const handleToggleRecord = useCallback(async () => {
    if (state.isRecording) {
      console.log('[TopBar] Stopping recording')
      stopAudio()
      onSessionEnd()
      dispatchUI({ type: 'SET_RECORDING', payload: false })
    } else {
      setIsStarting(true)
      try {
        console.log('[TopBar] Starting recording...')
        if (location.pathname !== '/sessions/current') {
          navigate('/sessions/current')
        }
        onSessionStart()
        await startAudio()
        dispatchUI({ type: 'SET_RECORDING', payload: true })
        console.log('[TopBar] Recording started successfully')
      } catch (err) {
        console.error('[TopBar] Failed to start recording:', err)
        toast.error('Failed to start recording — check mic permissions and console for details.')
      } finally {
        setIsStarting(false)
      }
    }
  }, [state.isRecording, startAudio, stopAudio, dispatchUI, onSessionEnd, onSessionStart, location.pathname, navigate])

  const handleNewSession = useCallback(() => {
    if (state.isRecording) {
      stopAudio()
      onSessionEnd()
    }
    dispatchUI({ type: 'RESET_SESSION' })
    navigate('/sessions/current')
  }, [state.isRecording, stopAudio, dispatchUI, onSessionEnd, navigate])

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-4 gap-3 shrink-0">
      <RecordButton
        isRecording={state.isRecording}
        isLoading={isStarting}
        onClick={handleToggleRecord}
      />

      <Button
        variant="outline"
        size="sm"
        onClick={handleNewSession}
        className="gap-2"
      >
        <Plus className="h-4 w-4" />
        <span className="hidden sm:inline">New Session</span>
      </Button>

      {/* Session name — editable, hidden on mobile */}
      <input
        className="hidden md:block text-sm font-medium bg-transparent border-none outline-none focus:ring-1 focus:ring-border rounded px-1 truncate max-w-xs text-foreground placeholder:text-muted-foreground"
        value={state.sessionName}
        onChange={(e) => dispatchUI({ type: 'SET_SESSION_NAME', payload: e.target.value })}
        placeholder="Session name"
        aria-label="Session name"
      />

      {/* Session theme — per-session context, shown when not recording */}
      {!state.isRecording && (
        <input
          className="hidden md:block text-xs bg-transparent border-none outline-none focus:ring-1 focus:ring-border rounded px-1 truncate max-w-[200px] text-muted-foreground placeholder:text-muted-foreground/60"
          value={state.config.theme}
          onChange={(e) => dispatchUI({ type: 'SET_CONFIG', payload: { theme: e.target.value } })}
          placeholder="Theme (meeting, D&D, lecture…)"
          aria-label="Session theme"
        />
      )}

      <div className="flex-1" />

      {/* Agent thinking indicator */}
      {state.isAgentThinking && (
        <Badge variant="secondary" className="gap-1.5 animate-pulse hidden sm:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
          Agent thinking…
        </Badge>
      )}

      <MicIndicator
        isRecording={state.isRecording}
        isReconnecting={state.isRecording && !isConnected}
      />

      <NavLink to="/settings">
        <Button variant="ghost" size="icon" aria-label="Open settings">
          <Settings className="h-4 w-4" />
        </Button>
      </NavLink>
    </header>
  )
}

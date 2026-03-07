import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { TopBar } from '@/components/topbar/TopBar'
import { MobileNav } from '@/components/sidebar/MobileNav'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useTTSPlayer } from '@/hooks/useTTSPlayer'
import { useAppContext } from '@/context/AppContext'
import { useCallback, useEffect, useRef } from 'react'
import type { WSEvent } from '@/store/types'
import { ErrorBanner } from '@/components/ErrorBanner'
import { Toaster } from '@/components/ui/sonner'
import { toast } from 'sonner'
import { getWsUrl } from '@/lib/auth'

const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
const WS_URL = getWsUrl(WS_BASE)

export function AppLayout() {
  const { dispatchWS, dispatchUI, state, registerSendJSON } = useAppContext()
  const { enqueue: enqueueTTS } = useTTSPlayer()
  const sendBinaryRef = useRef<(data: ArrayBuffer) => void>(() => {})

  const handleEvent = useCallback(
    (event: WSEvent) => {
      if (event.type === 'tts_chunk') {
        enqueueTTS(event.audio_b64)
        return
      }
      if (event.type === 'error' && !event.fatal) {
        toast.error(event.code, { description: event.message })
      }
      dispatchWS(event)
    },
    [dispatchWS, enqueueTTS]
  )

  const { sendBinary, sendJSON, isConnected } = useWebSocket({ url: WS_URL, onEvent: handleEvent })

  // Register sendJSON into context so any page (e.g. SettingsPage) can send WS messages
  useEffect(() => {
    registerSendJSON(sendJSON)
  }, [registerSendJSON, sendJSON])

  // Keep a stable callback ref so TopBar doesn't need sendBinary in its deps
  sendBinaryRef.current = sendBinary

  const handleSendBinary = useCallback((data: ArrayBuffer) => {
    sendBinaryRef.current(data)
  }, [])

  const handleRestart = useCallback(() => {
    dispatchUI({ type: 'RESET_SESSION' })
    sendJSON({ type: 'session_end' })
  }, [dispatchUI, sendJSON])

  const handleSessionStart = useCallback(() => {
    sendJSON({ type: 'session_start', config: state.config })
  }, [sendJSON, state.config])

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar
          onSendBinary={handleSendBinary}
          isConnected={isConnected}
          onSessionEnd={() => sendJSON({ type: 'session_end' })}
          onSessionStart={handleSessionStart}
        />
        {state.error?.fatal && (
          <ErrorBanner message={state.error.message} onRestart={handleRestart} />
        )}
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
        <MobileNav />
      </div>
      <Toaster />
    </div>
  )
}

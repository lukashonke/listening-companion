import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Plus, Mic } from 'lucide-react'
import { useAppContext } from '@/context/AppContext'
import { apiFetch } from '@/lib/auth'

interface ApiSession {
  id: string;
  name: string;
  created_at: number;
  ended_at: number | null;
}

export function SessionsPage() {
  const navigate = useNavigate()
  const { state } = useAppContext()
  const [historySessions, setHistorySessions] = useState<ApiSession[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)

  useEffect(() => {
    apiFetch('/api/sessions')
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((data: ApiSession[]) => setHistorySessions(data))
      .catch(err => console.warn('Failed to load session history:', err))
      .finally(() => setHistoryLoading(false))
  }, [])

  const hasActivity = state.transcript.length > 0 || state.toolLog.length > 0

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Sessions</h1>
          <Button size="sm" onClick={() => navigate('/sessions/current')} className="gap-2">
            <Plus className="h-4 w-4" />
            New Session
          </Button>
        </div>

        {hasActivity ? (
          <Card
            className="cursor-pointer hover:bg-accent/50 transition-colors border-border/70"
            onClick={() => navigate('/sessions/current')}
          >
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <Mic className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{state.sessionName}</p>
                <p className="text-xs text-muted-foreground">
                  {state.transcript.length} transcript chunks &middot; {state.shortTermMemory.length} memory entries
                </p>
              </div>
              <div
                className={`h-2 w-2 rounded-full shrink-0 ${
                  state.isRecording ? 'bg-red-500 animate-pulse' : 'bg-muted-foreground/30'
                }`}
              />
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
            <Mic className="h-12 w-12 text-muted-foreground/30" />
            <div>
              <p className="text-muted-foreground">No session active</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Start a new session to begin.
              </p>
            </div>
            <Button onClick={() => navigate('/sessions/current')} className="gap-2">
              <Plus className="h-4 w-4" />
              Start Session
            </Button>
          </div>
        )}

        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">Past Sessions</h2>
          {historyLoading ? (
            <p className="text-sm text-muted-foreground/70">Loading...</p>
          ) : historySessions.length === 0 ? (
            <p className="text-sm text-muted-foreground/70">No past sessions yet.</p>
          ) : (
            historySessions.map(session => {
              const duration = session.ended_at != null
                ? Math.round((session.ended_at - session.created_at) / 60)
                : null
              return (
                <Card
                  key={session.id}
                  className="border-border/70 cursor-pointer hover:bg-accent/50 transition-colors"
                  onClick={() => navigate(`/sessions/${session.id}`)}
                >
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                      <Mic className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{session.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(session.created_at * 1000).toLocaleString()}
                        {duration != null && <span> &middot; {duration} min</span>}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

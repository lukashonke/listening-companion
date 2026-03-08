import { useState, useEffect } from 'react'
import { useAppContext } from '@/context/AppContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Clock, FileText, Tag, User } from 'lucide-react'

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function nameSourceLabel(source: string): string {
  switch (source) {
    case 'auto': return 'Auto'
    case 'user': return 'User'
    default: return 'Default'
  }
}

function nameSourceVariant(source: string): 'default' | 'outline' | 'secondary' {
  switch (source) {
    case 'auto': return 'secondary'
    case 'user': return 'default'
    default: return 'outline'
  }
}

export function SessionMetadataPanel() {
  const { state } = useAppContext()
  const { sessionName, sessionNameSource, sessionSummary, sessionStatus, config } = state

  // Live duration timer
  const [sessionStartTime] = useState<number>(() => Date.now())
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (sessionStatus === 'idle') return

    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - sessionStartTime) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [sessionStatus, sessionStartTime])

  return (
    <div className="flex flex-col h-full gap-3 p-3" data-testid="session-metadata-panel">
      {/* Session Info Card */}
      <Card size="sm" className="shrink-0">
        <CardHeader className="border-b">
          <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Session Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-3">
          {/* Session Name */}
          <div className="flex items-start gap-2">
            <User className="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-xs text-muted-foreground">Name</p>
              <div className="flex items-center gap-1.5 flex-wrap">
                <p className="text-sm font-medium truncate" data-testid="session-name">{sessionName}</p>
                <Badge variant={nameSourceVariant(sessionNameSource)} className="text-[10px] h-4 px-1.5 shrink-0" data-testid="name-source-badge">
                  {nameSourceLabel(sessionNameSource)}
                </Badge>
              </div>
            </div>
          </div>

          {/* Duration */}
          <div className="flex items-start gap-2">
            <Clock className="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground">Duration</p>
              <p className="text-sm font-mono" data-testid="session-duration">
                {sessionStatus === 'idle' ? '—' : formatDuration(elapsed)}
              </p>
            </div>
          </div>

          {/* Theme */}
          {config.theme && (
            <div className="flex items-start gap-2">
              <Tag className="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs text-muted-foreground">Theme</p>
                <p className="text-sm truncate" data-testid="session-theme">{config.theme}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary Card */}
      <Card size="sm" className="flex-1 min-h-0 flex flex-col">
        <CardHeader className="border-b shrink-0">
          <CardTitle className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 pt-3">
          {sessionSummary ? (
            <ScrollArea className="h-full">
              <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap" data-testid="session-summary">
                {sessionSummary}
              </p>
            </ScrollArea>
          ) : (
            <div className="h-full flex items-center justify-center">
              <p className="text-xs text-muted-foreground text-center px-2" data-testid="summary-empty-state">
                Summary will appear after the first summarization cycle
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

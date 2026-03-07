import { useEffect, useRef } from 'react'
import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'
import { formatTime } from '@/lib/formatTime'

export function AgentLogTab() {
  const { state } = useAppContext()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [state.toolLog.length])

  return (
    <ScrollArea className="h-full">
      <div className="px-4 py-3 space-y-2 max-w-3xl mx-auto">
        {state.toolLog.length === 0 && !state.isAgentThinking && (
          <div className="flex items-center justify-center h-24 text-muted-foreground text-sm">
            No agent activity yet
          </div>
        )}
        {state.toolLog.map((event, i) => (
          <Card key={i} className="bg-card/50 border-border/50">
            <CardContent className="p-3 space-y-1.5">
              <div className="flex items-center gap-2">
                <Badge variant={event.error ? 'destructive' : 'secondary'} className="text-xs">
                  {event.tool}
                </Badge>
                <span className="text-xs text-muted-foreground font-mono ml-auto">
                  {formatTime(event.ts)}
                </span>
              </div>
              {Object.keys(event.args).length > 0 && (
                <pre className="text-xs text-muted-foreground bg-muted/50 rounded p-2 overflow-x-auto">
                  {JSON.stringify(event.args, null, 2)}
                </pre>
              )}
              {event.error && (
                <p className="text-xs text-destructive">Error: {event.error}</p>
              )}
            </CardContent>
          </Card>
        ))}
        {state.isAgentThinking && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Agent is processing\u2026
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}

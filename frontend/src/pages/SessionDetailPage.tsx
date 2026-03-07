import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ArrowLeft, Brain, FileText } from 'lucide-react'
import { apiFetch } from '@/lib/auth'

interface MemoryEntry {
  id: string
  content: string
  tags: string[]
  created_at: number
  updated_at: number
}

interface SessionDetail {
  id: string
  name: string
  created_at: number
  ended_at: number | null
  config: string
  memory: MemoryEntry[]
}

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [session, setSession] = useState<SessionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    apiFetch(`/api/sessions/${id}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: SessionDetail) => setSession(data))
      .catch(err => setError(String(err)))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
        Loading session…
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 text-muted-foreground">
        <p className="text-sm">Failed to load session.</p>
        <Button variant="outline" size="sm" onClick={() => navigate('/sessions')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Sessions
        </Button>
      </div>
    )
  }

  const duration = session.ended_at != null
    ? Math.round((session.ended_at - session.created_at) / 60)
    : null

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border px-4 py-3 flex items-center gap-3 shrink-0">
        <Button variant="ghost" size="sm" onClick={() => navigate('/sessions')} className="gap-1.5">
          <ArrowLeft className="h-4 w-4" />
          Sessions
        </Button>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{session.name || session.id}</p>
          <p className="text-xs text-muted-foreground">
            {new Date(session.created_at * 1000).toLocaleString()}
            {duration != null && <span> · {duration} min</span>}
          </p>
        </div>
      </div>

      <Tabs defaultValue="memory" className="flex flex-col flex-1 min-h-0">
        <div className="border-b border-border px-4 shrink-0">
          <TabsList className="bg-transparent h-10 p-0 gap-1 rounded-none">
            <TabsTrigger
              value="memory"
              className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10"
            >
              <Brain className="h-3.5 w-3.5" />
              Memory
              {session.memory.length > 0 && (
                <span className="text-xs text-muted-foreground ml-1">({session.memory.length})</span>
              )}
            </TabsTrigger>
            <TabsTrigger
              value="info"
              className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10"
            >
              <FileText className="h-3.5 w-3.5" />
              Info
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="memory" className="flex-1 mt-0 overflow-hidden data-[state=inactive]:hidden">
          {session.memory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-2 text-muted-foreground">
              <Brain className="h-8 w-8 opacity-30" />
              <span className="text-sm">No memory entries for this session</span>
            </div>
          ) : (
            <ScrollArea className="h-full">
              <div className="px-4 py-3 grid gap-2 max-w-3xl mx-auto sm:grid-cols-2">
                {session.memory.map((entry) => (
                  <Card key={entry.id} className="bg-card/50 border-border/50">
                    <CardContent className="p-3 space-y-2">
                      <p className="text-sm text-foreground leading-relaxed">{entry.content}</p>
                      {entry.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {entry.tags.map((tag) => (
                            <Badge key={tag} variant="outline" className="text-xs h-4 px-1.5">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}
        </TabsContent>

        <TabsContent value="info" className="flex-1 mt-0 overflow-auto data-[state=inactive]:hidden">
          <div className="px-4 py-3 max-w-xl space-y-3">
            <div className="text-sm space-y-1">
              <p className="text-muted-foreground text-xs uppercase tracking-wide font-medium">Session ID</p>
              <p className="font-mono text-xs">{session.id}</p>
            </div>
            <div className="text-sm space-y-1">
              <p className="text-muted-foreground text-xs uppercase tracking-wide font-medium">Started</p>
              <p>{new Date(session.created_at * 1000).toLocaleString()}</p>
            </div>
            {session.ended_at != null && (
              <div className="text-sm space-y-1">
                <p className="text-muted-foreground text-xs uppercase tracking-wide font-medium">Ended</p>
                <p>{new Date(session.ended_at * 1000).toLocaleString()}</p>
              </div>
            )}
            {session.config && (
              <div className="text-sm space-y-1">
                <p className="text-muted-foreground text-xs uppercase tracking-wide font-medium">Config</p>
                <pre className="text-xs bg-muted/50 rounded p-2 overflow-x-auto">
                  {JSON.stringify(JSON.parse(session.config), null, 2)}
                </pre>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

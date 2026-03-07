import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Brain, Clock } from 'lucide-react'
import { formatTime } from '@/lib/formatTime'

export function MemoryPage() {
  const { state } = useAppContext()

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border px-6 py-4 flex items-center gap-2 shrink-0">
        <Brain className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Memory</h1>
        <Badge variant="secondary" className="ml-auto">
          {state.shortTermMemory.length} entries
        </Badge>
      </div>

      {state.shortTermMemory.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
          <Brain className="h-10 w-10 opacity-20" />
          <p className="text-sm">No short-term memory entries yet</p>
          <p className="text-xs opacity-70">The agent will populate this as it listens</p>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <div className="p-6 grid gap-3 max-w-4xl mx-auto sm:grid-cols-2 lg:grid-cols-3">
            {state.shortTermMemory.map((entry) => (
              <Card key={entry.id} className="bg-card border-border/70">
                <CardHeader className="pb-2 pt-3 px-4">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>{formatTime(entry.updated_at)}</span>
                    <span className="ml-auto font-mono text-muted-foreground/50 truncate max-w-20">
                      {entry.id}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="px-4 pb-3 space-y-2">
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
    </div>
  )
}

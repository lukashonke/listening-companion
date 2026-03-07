import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Brain } from 'lucide-react'

export function MemoryTab() {
  const { state } = useAppContext()

  if (state.shortTermMemory.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 text-muted-foreground">
        <Brain className="h-8 w-8 opacity-30" />
        <span className="text-sm">No memory entries yet</span>
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="px-4 py-3 grid gap-2 max-w-3xl mx-auto sm:grid-cols-2">
        {state.shortTermMemory.map((entry) => (
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
  )
}

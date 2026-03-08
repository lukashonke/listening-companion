import { useEffect, useRef } from 'react'
import { useAppContext } from '@/context/AppContext'
import { Badge } from '@/components/ui/badge'
import { formatTime } from '@/lib/formatTime'

export function TranscriptTab() {
  const { state } = useAppContext()
  const bottomRef = useRef<HTMLDivElement>(null)
  const viewportRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = viewportRef.current
    if (!el) return
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
    if (isNearBottom) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [state.transcript.length])

  if (state.transcript.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
        {state.isRecording ? 'Listening\u2026' : 'Start recording to see the transcript'}
      </div>
    )
  }

  return (
    <div ref={viewportRef} className="h-full overflow-y-auto">
      <div className="px-4 py-3 space-y-2 max-w-3xl mx-auto">
        {state.transcript.map((chunk, i) => (
          <div key={`${chunk.ts}-${i}`} className="flex gap-3 items-start">
            <span className="text-xs text-muted-foreground mt-0.5 shrink-0 font-mono w-16">
              {formatTime(chunk.ts)}
            </span>
            {chunk.speaker && (
              <Badge variant="outline" className="shrink-0 text-xs h-5 mt-0.5">
                {chunk.speaker}
              </Badge>
            )}
            <p className="text-sm text-foreground leading-relaxed">{chunk.text}</p>
          </div>
        ))}
        {state.isRecording && (
          <div className="flex gap-3 items-center py-1">
            <span className="shrink-0 w-16" />
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="inline-block h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              Listening\u2026
            </span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

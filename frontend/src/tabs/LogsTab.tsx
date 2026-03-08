import { useEffect, useRef, useState } from 'react'
import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import type { LogLevel } from '@/store/types'
import { formatTime } from '@/lib/formatTime'

const levelClass: Record<LogLevel, string> = {
  DEBUG: 'text-muted-foreground',
  INFO: 'text-foreground',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-500 font-bold',
}

export function LogsTab() {
  const { state, dispatchUI } = useAppContext()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [state.logs.length, autoScroll])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border shrink-0">
        <span className="text-xs text-muted-foreground">{state.logs.length} entries</span>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          className="text-xs h-7"
          onClick={() => setAutoScroll((v) => !v)}
        >
          Auto-scroll: {autoScroll ? 'on' : 'off'}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs h-7"
          onClick={() => dispatchUI({ type: 'CLEAR_LOGS' })}
        >
          Clear
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="px-4 py-2 font-mono text-xs space-y-0.5">
          {state.logs.length === 0 && (
            <div className="flex items-center justify-center h-24 text-muted-foreground">
              No logs yet — start a session to see backend output
            </div>
          )}
          {state.logs.map((entry, i) => (
            <div key={i} className="flex gap-2 leading-5">
              <span className="text-muted-foreground shrink-0">{formatTime(entry.ts)}</span>
              <span className={`shrink-0 w-16 ${levelClass[entry.level]}`}>{entry.level}</span>
              <span className={`break-all ${levelClass[entry.level]}`}>{entry.message}</span>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  )
}

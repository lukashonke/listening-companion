import { cn } from '@/lib/utils'

interface MicIndicatorProps {
  isRecording: boolean
  isReconnecting?: boolean
}

export function MicIndicator({ isRecording, isReconnecting }: MicIndicatorProps) {
  if (isReconnecting) {
    return (
      <div className="flex items-center gap-1.5">
        <div className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
        <span className="text-xs text-muted-foreground">Reconnecting…</span>
      </div>
    )
  }

  if (isRecording) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
        </span>
        <span className="text-xs text-muted-foreground">Recording</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5">
      <div className={cn('h-2 w-2 rounded-full bg-muted-foreground/30')} />
      <span className="text-xs text-muted-foreground">Idle</span>
    </div>
  )
}

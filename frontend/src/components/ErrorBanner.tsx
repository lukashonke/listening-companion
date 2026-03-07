import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ErrorBannerProps {
  message: string
  onRestart: () => void
}

export function ErrorBanner({ message, onRestart }: ErrorBannerProps) {
  return (
    <div className="bg-destructive/15 border-b border-destructive/30 px-4 py-2 flex items-center gap-3 shrink-0">
      <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
      <span className="text-sm text-destructive flex-1 min-w-0 truncate">{message}</span>
      <Button variant="destructive" size="sm" onClick={onRestart} className="shrink-0">
        Restart Session
      </Button>
    </div>
  )
}

import { Mic, MicOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface RecordButtonProps {
  isRecording: boolean
  isLoading?: boolean
  onClick: () => void
}

export function RecordButton({ isRecording, isLoading, onClick }: RecordButtonProps) {
  return (
    <Button
      variant={isRecording ? 'destructive' : 'default'}
      size="sm"
      onClick={onClick}
      disabled={isLoading}
      className="gap-2"
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : isRecording ? (
        <MicOff className="h-4 w-4" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
      <span>{isLoading ? 'Starting…' : isRecording ? 'Stop' : 'Start'}</span>
    </Button>
  )
}

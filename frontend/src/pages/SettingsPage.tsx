import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Settings } from 'lucide-react'

export function SettingsPage() {
  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Settings</h1>
        </div>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-sm">WebSocket Connection</CardTitle>
            <CardDescription>Backend connection settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Endpoint</span>
              <code className="text-xs bg-muted px-2 py-0.5 rounded font-mono">
                ws://localhost:8000/ws
              </code>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-sm">Audio Capture</CardTitle>
            <CardDescription>Microphone settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Sample Rate</span>
              <Badge variant="secondary">16 kHz</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Format</span>
              <Badge variant="secondary">PCM 16-bit mono</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Chunk size</span>
              <Badge variant="secondary">200ms</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-sm">About</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-1">
            <p>Listening Companion &mdash; AI-powered real-time conversation assistant</p>
            <p className="text-xs opacity-70">
              Backend: FastAPI + Pydantic AI + Claude &middot; STT: ElevenLabs Scribe
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

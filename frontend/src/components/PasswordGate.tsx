import { useState, useEffect, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { getPassword, setPassword, apiFetch } from '@/lib/auth'

interface Props {
  children: ReactNode
}

export function PasswordGate({ children }: Props) {
  const [state, setState] = useState<'checking' | 'ok' | 'prompt'>('checking')
  const [input, setInput] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    // Quick auth check — if server has no password, /health always passes
    // Try /api/sessions with current password to see if auth is required
    apiFetch('/api/sessions', { method: 'HEAD' })
      .catch(() => apiFetch('/api/sessions'))
      .then(r => {
        if (r.status === 401) {
          setState('prompt')
        } else {
          setState('ok')
        }
      })
      .catch(() => setState('ok'))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setPassword(input)
    const r = await apiFetch('/api/sessions').catch(() => null)
    if (!r || r.status === 401) {
      setPassword('')
      setError('Incorrect password')
    } else {
      setState('ok')
    }
  }

  if (state === 'checking') {
    return (
      <div className="h-screen flex items-center justify-center text-muted-foreground text-sm">
        Connecting…
      </div>
    )
  }

  if (state === 'prompt') {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-xs space-y-4 p-6 rounded-xl border bg-card shadow-sm"
        >
          <div>
            <h1 className="text-lg font-semibold">Listening Companion</h1>
            <p className="text-sm text-muted-foreground mt-1">Enter password to continue</p>
          </div>
          <input
            type="password"
            autoFocus
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Password"
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
          />
          {error && <p className="text-xs text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={!input}>
            Unlock
          </Button>
        </form>
      </div>
    )
  }

  return <>{children}</>
}

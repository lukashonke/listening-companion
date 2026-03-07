# Phase 3: Frontend–Backend Wiring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Connect the React frontend and FastAPI backend end-to-end: fix protocol mismatches, add interactive Settings, wire Sessions page to REST API, and add Docker/Fly.io deployment files.

**Architecture:** Frontend talks to backend via `ws://localhost:8000/ws` (WebSocket for real-time) and `http://localhost:8000/api/*` (REST for history). In dev, Vite proxies `/ws` and `/api` to port 8000. In production, FastAPI serves the built `frontend/dist/` at `/`. A single Docker container builds the frontend then runs uvicorn.

**Tech Stack:** React 18, Vite 7, TypeScript 5, FastAPI, uvicorn, Docker multi-stage build, Fly.io, docker-compose

---

## Current State Summary

**Already working (no changes needed):**
- WS binary audio frames → backend STT
- `transcript_chunk` → TranscriptTab renders
- `tool_call`/`agent_start`/`agent_done` → AgentLogTab renders
- `memory_update` → MemoryTab renders
- `image_generated` → ImagesPage renders
- `tts_chunk` → useTTSPlayer plays audio
- `session_status` → TopBar updates
- `error` → ErrorBanner displays

**Must fix:**
1. `image_provider` hardcoded as `"fal"` in AppLayout — backend only supports `"placeholder"` → change to `"placeholder"`
2. `ToolEvent.result` TypeScript type too strict (`Record<string,unknown>`) — backend sends `string|null` too → loosen type
3. Settings page is read-only — needs interactive controls that send `config_update`
4. Sessions page reads local state — needs to query `GET /api/sessions`
5. Vite dev server has no proxy → add `/ws` and `/api` proxies

**New files:**
- `Dockerfile` (multi-stage: Node build → Python serve)
- `fly.toml`
- `docker-compose.yml`
- `backend/.env.example` (already exists, verify)

---

## Task 1: Fix TypeScript protocol types

**Why:** `ToolEvent.result` is typed as `Record<string,unknown>` but backend sends `string | null | dict`. This causes TypeScript errors and potential runtime crashes in AgentLogTab.

**Files:**
- Modify: `frontend/src/store/types.ts`

**Step 1: Read the file**

```bash
cat /home/lukashonke/projects/listening-companion/claude-code/frontend/src/store/types.ts
```

**Step 2: Edit ToolEvent to loosen result type**

Find the `ToolEvent` interface (or the `tool_call` variant in WSEvent). Change:
```typescript
// Before:
result: Record<string, unknown>;
// After:
result: Record<string, unknown> | string | null;
```

Also find where `tool_call` is in the `WSEvent` discriminated union and ensure `result` there is also `Record<string, unknown> | string | null`.

**Step 3: Build frontend to check no type errors**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code/frontend
npm run build 2>&1 | tail -20
```

Expected: Build succeeds (exit 0).

**Step 4: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/store/types.ts
git commit -m "fix(frontend): loosen ToolEvent.result type to match backend (string|null|dict)"
```

---

## Task 2: Fix image_provider default + add config state to context

**Why:** AppLayout hardcodes `image_provider: "fal"` but backend only supports `"placeholder"`. Also, settings need to live in React state so Settings page can control them.

**Files:**
- Modify: `frontend/src/store/types.ts` (add SessionConfig type + AppState field)
- Modify: `frontend/src/store/reducer.ts` (add SET_CONFIG action)
- Modify: `frontend/src/context/AppContext.tsx` (if needed for new action)
- Modify: `frontend/src/app/AppLayout.tsx` (read config from state instead of hardcoding)

**Step 1: Read all relevant files first**

```bash
cat frontend/src/store/types.ts
cat frontend/src/store/reducer.ts
cat frontend/src/app/AppLayout.tsx
cat frontend/src/context/AppContext.tsx
```

**Step 2: Add SessionConfig to types.ts**

Add this interface near the top of `types.ts` (after existing imports):

```typescript
export interface SessionConfig {
  voice_id: string;
  agent_interval_s: number;
  image_provider: string;
  tools: string[];
  speaker_diarization: boolean;
}
```

Add `config: SessionConfig` to `AppState`:

```typescript
// In AppState interface, add:
config: SessionConfig;
```

Add `SET_CONFIG` to the UI action union:

```typescript
// In UIAction type:
| { type: 'SET_CONFIG'; payload: Partial<SessionConfig> }
```

**Step 3: Add initialConfig and SET_CONFIG handler in reducer.ts**

In `reducer.ts`, add to `initialState`:

```typescript
config: {
  voice_id: 'JBFqnCBsd6RMkjVDRZzb',
  agent_interval_s: 30,
  image_provider: 'placeholder',
  tools: [],
  speaker_diarization: false,
},
```

Add case in `uiReducer` (or wherever UI actions are handled):

```typescript
case 'SET_CONFIG':
  return { ...state, config: { ...state.config, ...action.payload } };
```

**Step 4: Update AppLayout.tsx to use state.config**

Find where `session_start` is sent (the `onSessionStart` function or similar). Replace the hardcoded config object with `state.config`:

```typescript
// Before (hardcoded):
sendJSON({ type: 'session_start', config: {
  tools: [],
  voice_id: 'JBFqnCBsd6RMkjVDRZzb',
  agent_interval_s: 30,
  image_provider: 'fal',
  speaker_diarization: false,
}});

// After (from state):
sendJSON({ type: 'session_start', config: state.config });
```

Also find where `config_update` might need to be sent when config changes during a session (if recording is active and config changes, send config_update). We'll wire this from the Settings page in Task 4.

**Step 5: Build and check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

**Step 6: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/store/types.ts frontend/src/store/reducer.ts frontend/src/app/AppLayout.tsx
git commit -m "feat(frontend): add SessionConfig to state, fix image_provider to 'placeholder'"
```

---

## Task 3: Add Vite dev proxy for /ws and /api

**Why:** Without a proxy, running `npm run dev` on port 5173 cannot connect to the backend on port 8000 (CORS for WS, different origin for API calls).

**Files:**
- Modify: `frontend/vite.config.ts`

**Step 1: Read vite.config.ts**

```bash
cat /home/lukashonke/projects/listening-companion/claude-code/frontend/vite.config.ts
```

**Step 2: Add proxy config**

In the `defineConfig`, add a `server.proxy` block:

```typescript
server: {
  proxy: {
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true,
      rewriteWsOrigin: true,
    },
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

**Step 3: Also update useWebSocket.ts WS URL**

The URL is hardcoded as `ws://localhost:8000/ws`. In dev (behind Vite proxy), it should use the current host. Change the URL construction so it works both ways:

Read `frontend/src/hooks/useWebSocket.ts` first, then in `AppLayout.tsx` (where `useWebSocket` is called), update the URL:

```typescript
// Derive WS URL from current page location so it works behind proxy:
const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
```

If `useWebSocket` is called in `AppLayout.tsx` with a hardcoded URL, change that. If the URL is a prop passed in, change where it's constructed.

**Step 4: Build and verify no TypeScript errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

**Step 5: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/vite.config.ts frontend/src/app/AppLayout.tsx frontend/src/hooks/useWebSocket.ts
git commit -m "feat(frontend): Vite dev proxy for /ws and /api, dynamic WS URL"
```

---

## Task 4: Make Settings page interactive

**Why:** Settings page is currently read-only. Users need to configure voice ID, agent interval, image provider, and tools before starting a session.

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/app/AppLayout.tsx` (wire config_update if recording)

**Step 1: Read SettingsPage.tsx and AppLayout.tsx**

```bash
cat frontend/src/pages/SettingsPage.tsx
cat frontend/src/app/AppLayout.tsx
```

**Step 2: Rewrite SettingsPage.tsx with interactive controls**

Replace the read-only content with a settings form. Use `useAppContext()` to read state and dispatch changes. When a setting changes, dispatch `SET_CONFIG`. If currently recording (`state.isRecording`), also send `config_update` via the `sendJSON` function (expose it from context or pass as prop).

Key controls to add:
- **Voice ID**: text input, bound to `state.config.voice_id`
- **Agent Interval**: number select (10s, 30s, 60s), bound to `state.config.agent_interval_s`
- **Image Provider**: select (placeholder, fal, openai), bound to `state.config.image_provider`
- **Speaker Diarization**: toggle/switch, bound to `state.config.speaker_diarization`

Full replacement for `SettingsPage.tsx`:

```typescript
import { useAppContext } from '@/context/AppContext';

const AGENT_INTERVALS = [10, 30, 60, 120];
const IMAGE_PROVIDERS = [
  { value: 'placeholder', label: 'Placeholder (no API key needed)' },
  { value: 'fal', label: 'fal.ai (Flux)' },
  { value: 'openai', label: 'OpenAI (gpt-image-1)' },
];

export default function SettingsPage() {
  const { state, dispatchUI, sendJSON } = useAppContext();
  const { config, isRecording } = state;

  const updateConfig = (patch: Partial<typeof config>) => {
    dispatchUI({ type: 'SET_CONFIG', payload: patch });
    if (isRecording) {
      sendJSON({ type: 'config_update', config: patch });
    }
  };

  return (
    <div className="p-6 max-w-lg space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <div className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium">Voice ID (ElevenLabs)</label>
          <input
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.voice_id}
            onChange={e => updateConfig({ voice_id: e.target.value })}
            placeholder="JBFqnCBsd6RMkjVDRZzb"
          />
          <p className="text-xs text-muted-foreground">ElevenLabs voice ID for TTS responses</p>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">Agent Interval</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.agent_interval_s}
            onChange={e => updateConfig({ agent_interval_s: Number(e.target.value) })}
          >
            {AGENT_INTERVALS.map(s => (
              <option key={s} value={s}>{s}s</option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">How often the AI agent reviews the transcript</p>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">Image Provider</label>
          <select
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
            value={config.image_provider}
            onChange={e => updateConfig({ image_provider: e.target.value })}
          >
            {IMAGE_PROVIDERS.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Speaker Diarization</p>
            <p className="text-xs text-muted-foreground">Label speakers A, B, C in transcript</p>
          </div>
          <button
            onClick={() => updateConfig({ speaker_diarization: !config.speaker_diarization })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              config.speaker_diarization ? 'bg-primary' : 'bg-muted'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              config.speaker_diarization ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>
      </div>

      {isRecording && (
        <p className="text-xs text-amber-500">Settings are applied live to the current session.</p>
      )}
    </div>
  );
}
```

**Step 3: Expose sendJSON from AppContext**

Read `AppContext.tsx`. The `sendJSON` function from `useWebSocket` needs to be available in the context so SettingsPage can send `config_update`. If it's not already exposed, add it.

In `AppContext.tsx`:
- Add `sendJSON` to the context value
- SettingsPage accesses it via `useAppContext()`

**Step 4: Build and check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

**Step 5: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/pages/SettingsPage.tsx frontend/src/context/AppContext.tsx
git commit -m "feat(frontend): interactive Settings page with live config_update support"
```

---

## Task 5: Wire Sessions page to REST API

**Why:** SessionsPage currently shows sessions derived from local state only. The backend has `GET /api/sessions` that returns persisted session history.

**Files:**
- Modify: `frontend/src/pages/SessionsPage.tsx`

**Step 1: Read SessionsPage.tsx**

```bash
cat frontend/src/pages/SessionsPage.tsx
```

**Step 2: Add API fetch for session history**

Augment `SessionsPage.tsx` to fetch historical sessions from `GET /api/sessions` and show them alongside the current session. Use `useEffect` + `fetch`:

```typescript
import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/AppContext';

interface ApiSession {
  id: string;
  name: string;
  created_at: number;
  ended_at: number | null;
}

export default function SessionsPage() {
  const { state } = useAppContext();
  const [historySessions, setHistorySessions] = useState<ApiSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/sessions')
      .then(r => r.json())
      .then((data: ApiSession[]) => setHistorySessions(data))
      .catch(err => console.warn('Failed to load session history:', err))
      .finally(() => setLoading(false));
  }, []);

  const hasCurrentSession = state.transcript.length > 0 || state.toolLog.length > 0;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Sessions</h1>

      {/* Current session card (existing logic, keep it) */}
      {hasCurrentSession && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground mb-2">Current Session</h2>
          {/* existing current session card */}
        </div>
      )}

      {/* Historical sessions from API */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground mb-2">History</h2>
        {loading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!loading && historySessions.length === 0 && (
          <p className="text-sm text-muted-foreground">No past sessions yet.</p>
        )}
        <div className="space-y-2">
          {historySessions.map(s => (
            <div key={s.id} className="rounded-lg border p-4 space-y-1">
              <p className="text-sm font-medium">{s.name || s.id}</p>
              <p className="text-xs text-muted-foreground">
                {new Date(s.created_at * 1000).toLocaleString()}
                {s.ended_at ? ` — ${Math.round((s.ended_at - s.created_at) / 60)}min` : ' (ongoing)'}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**IMPORTANT:** Keep all the existing current-session card logic from the original file. Only augment it with the historical sessions section. Read the existing file carefully before rewriting.

**Step 3: Build and check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

**Step 4: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add frontend/src/pages/SessionsPage.tsx
git commit -m "feat(frontend): Sessions page fetches history from GET /api/sessions"
```

---

## Task 6: Add Dockerfile (multi-stage build)

**Why:** Single Docker container that builds frontend, then serves everything from the FastAPI backend.

**Files:**
- Create: `Dockerfile` (at repo root)
- Create: `.dockerignore`

**Step 1: Create Dockerfile at repo root**

```dockerfile
# ── Stage 1: Build frontend ───────────────────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Backend runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS backend

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/backend
COPY backend/pyproject.toml backend/.python-version ./
RUN uv sync --no-dev

COPY backend/ ./

# Copy built frontend into the location backend expects
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

ENV FRONTEND_DIST=/app/frontend/dist
ENV DATABASE_PATH=/data/listening_companion.db

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Create .dockerignore at repo root**

```
.git
**/node_modules
**/__pycache__
**/*.pyc
**/.venv
**/dist
backend/.env
backend/*.db
frontend/.next
```

**Step 3: Verify Dockerfile builds (if Docker is available)**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
docker build -t listening-companion . 2>&1 | tail -20
```

If Docker is not available, skip the build test and just commit. Note this in your report.

**Step 4: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add Dockerfile .dockerignore
git commit -m "feat: multi-stage Dockerfile (Node build frontend → Python serve)"
```

---

## Task 7: Add fly.toml

**Why:** Deploy to Fly.io with persistent SQLite volume.

**Files:**
- Create: `fly.toml` (at repo root)

**Step 1: Create fly.toml**

```toml
app = "listening-companion"
primary_region = "ams"

[build]

[env]
  PORT = "8000"
  FRONTEND_DIST = "/app/frontend/dist"

[mounts]
  source = "listening_companion_data"
  destination = "/data"

[[services]]
  protocol = "tcp"
  internal_port = 8000
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [services.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

**Step 2: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add fly.toml
git commit -m "feat: fly.toml for Fly.io deployment with persistent SQLite volume"
```

---

## Task 8: Add docker-compose.yml for local development

**Why:** Single command to start both frontend dev server and backend together.

**Files:**
- Create: `docker-compose.yml` (at repo root)

**Step 1: Create docker-compose.yml**

```yaml
version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
      target: backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - listening_companion_data:/data
    env_file:
      - backend/.env
    environment:
      - FRONTEND_DIST=/app/frontend/dist
      - DATABASE_PATH=/data/listening_companion.db
    command: uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    image: node:22-alpine
    working_dir: /app
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host 0.0.0.0
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  listening_companion_data:
```

**Step 2: Commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add docker-compose.yml
git commit -m "feat: docker-compose.yml for local development"
```

---

## Task 9: End-to-end integration test

**Why:** Verify everything works together before calling Phase 3 complete.

**Step 1: Build the frontend**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code/frontend
npm run build 2>&1
```

Expected: `✓ built in Xs` — no errors.

**Step 2: Start the backend (background)**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code/backend
cp ~/.openclaw/.env .env 2>/dev/null || true
uv run uvicorn main:app --port 8000 &
BACKEND_PID=$!
sleep 3
```

**Step 3: Test health endpoint**

```bash
curl -s http://localhost:8000/health
```

Expected: `{"status":"ok"}`

**Step 4: Test sessions API**

```bash
curl -s http://localhost:8000/api/sessions
```

Expected: JSON array (may be empty `[]`).

**Step 5: Test frontend static serving**

```bash
curl -s http://localhost:8000/ | head -5
```

Expected: HTML with `<!DOCTYPE html>` — the built React app.

**Step 6: Test WebSocket handshake**

```bash
# Use websocat if available, otherwise use Python
python3 -c "
import asyncio, json, websockets

async def test():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        # Send session_start
        await ws.send(json.dumps({
            'type': 'session_start',
            'config': {
                'tools': [],
                'voice_id': 'test',
                'agent_interval_s': 3600,
                'image_provider': 'placeholder',
                'speaker_diarization': False
            }
        }))
        # Expect session_status: listening
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(msg)
        print('Got event:', data.get('type'), data.get('state', ''))
        assert data['type'] == 'session_status', f'Expected session_status, got {data[\"type\"]}'
        assert data['state'] == 'listening'
        # Send session_end
        await ws.send(json.dumps({'type': 'session_end'}))
        print('WebSocket test PASSED')

asyncio.run(test())
"
```

Expected: `Got event: session_status listening` then `WebSocket test PASSED`.

**Step 7: Stop backend**

```bash
kill $BACKEND_PID 2>/dev/null || true
```

**Step 8: Run frontend tests**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code/frontend
npm run test:run 2>&1 | tail -20
```

Expected: All tests pass.

**Step 9: Final commit**

```bash
cd /home/lukashonke/projects/listening-companion/claude-code
git add -A
git status  # verify nothing sensitive (.env, .db) is staged
git commit -m "feat: Phase 3 complete — frontend+backend wired end-to-end

- Fix ToolEvent.result type (string|null|dict)
- Fix image_provider default to 'placeholder'
- Add SessionConfig to React state (SET_CONFIG action)
- Vite dev proxy for /ws and /api routes
- Dynamic WS URL from window.location
- Interactive Settings page with live config_update
- Sessions page fetches history from GET /api/sessions
- Multi-stage Dockerfile (Node build + Python serve)
- fly.toml for Fly.io with persistent SQLite volume
- docker-compose.yml for local development
- End-to-end WS handshake verified"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] `npm run build` in `frontend/` succeeds with zero TS errors
- [ ] `uv run pytest tests/` in `backend/` shows 28/28 passing
- [ ] `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] `curl http://localhost:8000/` returns HTML (frontend served by backend)
- [ ] WebSocket handshake test returns `session_status: listening`
- [ ] `curl http://localhost:8000/api/sessions` returns valid JSON array
- [ ] All frontend tests pass

---

## Key File Paths Reference

| File | Purpose |
|---|---|
| `frontend/src/store/types.ts` | TypeScript types for WS events and state |
| `frontend/src/store/reducer.ts` | State reducer, initialState |
| `frontend/src/app/AppLayout.tsx` | WS bootstrap, audio capture, session_start |
| `frontend/src/context/AppContext.tsx` | React context, sendJSON exposure |
| `frontend/src/pages/SettingsPage.tsx` | Settings form → config_update |
| `frontend/src/pages/SessionsPage.tsx` | Session history → /api/sessions |
| `frontend/vite.config.ts` | Dev proxy config |
| `Dockerfile` | Multi-stage build |
| `fly.toml` | Fly.io deployment |
| `docker-compose.yml` | Local dev |

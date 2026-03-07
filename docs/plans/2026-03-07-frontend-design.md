# Listening Companion — Frontend Design

**Date:** 2026-03-07
**Approach:** Approach A — React Router page-based navigation

---

## Architecture

**Stack:** Vite + React + TypeScript + shadcn/ui + Tailwind CSS + React Router v6

**Layout shell:** Persistent `AppLayout` component containing:
- Collapsible left sidebar (icons-only collapsed, icons+labels expanded)
- Top action bar
- Main area (router `<Outlet />`)

**Pages (router routes):**
- `/` → redirect to `/sessions`
- `/sessions` → Session history list (past sessions)
- `/sessions/current` → Active session view with 3 tabs (Transcript / Agent Log / Memory)
- `/memory` → Full memory management page
- `/images` → Image gallery page
- `/settings` → Settings configuration page

**Active session tabs (only on `/sessions/current`):**
- Transcript — live auto-scrolling, timestamps, speaker labels
- Agent Log — tool calls, TTS events, agent start/done
- Memory — short-term memory cards (live-updated)

---

## State Management

`useReducer` with WebSocket dispatch table (per ARCHITECTURE.md):

```typescript
type AppState = {
  sessionStatus: "idle" | "listening" | "processing"
  transcript: TranscriptChunk[]
  shortTermMemory: MemoryEntry[]
  toolLog: ToolEvent[]
  images: GeneratedImage[]
  isAgentThinking: boolean
  error: AppError | null
}
```

Handlers: `transcript_chunk`, `memory_update`, `tool_call`, `image_generated`, `agent_start`, `agent_done`, `session_status`, `error`, `tts_chunk`

---

## Custom Hooks

| Hook | Responsibility |
|------|---------------|
| `useWebSocket` | WS connection to `ws://localhost:8000/ws`, exponential backoff reconnect (1s→2s→4s→max 30s), dispatches JSON events to reducer |
| `useAudioCapture` | AudioWorklet setup, sends binary PCM frames (16kHz/16-bit/mono) over WebSocket |
| `useTTSPlayer` | Receives `tts_chunk` base64 audio, decodes and plays via Web Audio API |

---

## Component Tree

```
AppLayout
├── Sidebar (collapsible, icon-nav)
├── TopBar
│   ├── RecordButton (Start/Stop toggle)
│   ├── NewSessionButton
│   ├── SessionNameDisplay
│   ├── MicStatusIndicator (pulsing red dot when recording)
│   └── SettingsGearIcon
└── MainArea (router Outlet)
    ├── SessionsPage (list of past sessions)
    ├── ActiveSessionPage
    │   └── Tabs: TranscriptTab | AgentLogTab | MemoryTab
    ├── MemoryPage (full memory management)
    ├── ImagesPage (gallery)
    └── SettingsPage (config)
```

---

## Dark Theme

- Tailwind `dark` class on `<html>` element (class strategy)
- shadcn/ui components use CSS variables — set dark theme as default (no light/dark toggle needed initially)
- All custom components use Tailwind dark-mode utilities

---

## Error Handling (Frontend)

- Non-fatal errors → dismissible toast (shadcn Toast)
- Fatal errors (`error.fatal: true`) → persistent banner with "Restart Session" button
- WebSocket disconnected while recording → reconnecting spinner overlaid on mic indicator

---

## Mobile Responsiveness

- Sidebar → bottom navigation bar on `sm:` breakpoint
- Tabs remain, stack vertically if needed
- Top bar collapses session name on mobile

---

## File Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── App.tsx              # Router setup
│   │   ├── AppLayout.tsx        # Shell: sidebar + topbar + outlet
│   │   └── routes.tsx           # Route definitions
│   ├── components/
│   │   ├── sidebar/
│   │   │   └── Sidebar.tsx
│   │   ├── topbar/
│   │   │   └── TopBar.tsx
│   │   └── ui/                  # shadcn/ui generated components
│   ├── pages/
│   │   ├── SessionsPage.tsx
│   │   ├── ActiveSessionPage.tsx
│   │   ├── MemoryPage.tsx
│   │   ├── ImagesPage.tsx
│   │   └── SettingsPage.tsx
│   ├── tabs/
│   │   ├── TranscriptTab.tsx
│   │   ├── AgentLogTab.tsx
│   │   └── MemoryTab.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useAudioCapture.ts
│   │   └── useTTSPlayer.ts
│   ├── store/
│   │   ├── reducer.ts           # useReducer + dispatch table
│   │   └── types.ts             # AppState, all WS event types
│   ├── context/
│   │   └── AppContext.tsx       # Context provider wrapping reducer
│   └── main.tsx
├── public/
│   └── audio-processor.worklet.js
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.ts
```

---

## Design Decisions

- **React Router v6** for page navigation (URLs change per nav item)
- **Context API** to share AppState + dispatch from `useReducer` without prop drilling
- **No Zustand** — spec requires `useReducer`; Context is sufficient
- **shadcn/ui** dark theme as default (no toggle needed for v1)
- **Audio worklet** wired up but non-functional without backend (as specified)
- **Ring buffer** for tool log: last 100 entries max
- **Auto-scroll** on Transcript tab: `useEffect` + `scrollIntoView` on new chunks

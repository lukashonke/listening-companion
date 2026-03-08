# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ElevenLabs Endpoints — DO NOT CHANGE

The correct ElevenLabs EU endpoints are:

- **TTS:** `https://api.eu.residency.elevenlabs.io`
- **STT (WebSocket):** `wss://api.eu.residency.elevenlabs.io`

These are defined in `backend/config.py`. **Never change them.** The domain `api.eu.elevenlabs.io` does NOT exist (NXDOMAIN). The `residency` subdomain is the correct one.

## STT Model

The STT model is `scribe_v2_realtime`. Do not downgrade to `scribe_v1`.

---

## Commands

### Backend

```bash
cd backend
uv sync                              # install dependencies
uv run uvicorn main:app --reload     # run dev server (port 8000)
uv run pytest                        # run all tests
uv run pytest tests/test_memory.py   # run a single test file
uv run pytest -k "test_name"         # run a single test by name
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Vite dev server
npm run build        # TypeScript check + production build
npm run lint         # ESLint
npm run test:run     # Vitest (single run, no watch)
npm test             # Vitest (watch mode)
```

---

## Architecture Overview

A real-time AI listening agent. One persistent WebSocket connection per session: binary PCM audio frames go up, JSON events come back down.

```
Browser mic → AudioWorklet → WebSocket (binary PCM, 16kHz/16-bit/mono/200ms chunks)
                                     ↓
                            FastAPI ws_handler.py
                               ↙           ↘
                         stt.py            Every N seconds:
                    (ElevenLabs Scribe)    agent.py (Pydantic AI + Claude)
                    → transcript_buffer         ↓ tools/
                                          memory ops, TTS, image gen
                                               ↓
                            JSON events → Frontend React state
```

### Backend (`backend/`)

| File | Role |
|---|---|
| `main.py` | FastAPI app, mounts `/ws` endpoint |
| `ws_handler.py` | Owns the WebSocket lifecycle per session; routes binary frames to STT, schedules agent timer |
| `agent.py` | Builds and invokes the Pydantic AI agent; auto-discovers tools from `tools/`; emits `tool_call` / `agent_start` / `agent_done` events |
| `stt.py` | Streams PCM to ElevenLabs Scribe WebSocket; emits `transcript_chunk` events |
| `tts.py` | Calls ElevenLabs TTS REST; streams base64 chunks back as `tts_chunk` events |
| `config.py` | Pydantic settings; source of truth for all endpoints and model names |
| `memory/short_term.py` | In-memory dict, SQLite-backed; injected into every agent invocation |
| `memory/long_term.py` | SQLite + sqlite-vec embeddings (sentence-transformers, local, no API cost) |
| `image_gen.py` | Pluggable image provider (fal.ai, OpenAI, Vertex) |
| `models.py` | Shared Pydantic models |
| `database.py` | aiosqlite setup |

### Tool System

Drop a `@tool`-decorated function in `tools/` and it auto-registers. No other config needed.

```python
# tools/my_tool.py
from api.tools import tool

@tool(tags=["plugin"])
def my_tool(arg: str) -> str:
    """Docstring becomes the LLM tool description."""
    return "result"
```

Core tools (always active): `save_short_term_memory`, `remove_short_term_memory`, `update_short_term_memory`, `save_long_term_memory`, `search_long_term_memory`, `answer_tts`, `generate_image`.

Session config's `tools` list activates additional plugin tools from `tools/` by function name. Restart the server to pick up new tools.

### WebSocket Protocol

**Client → Server**
- Binary: raw PCM audio
- `session_start` with `{tools, voice_id, agent_interval_s, image_provider, speaker_diarization}`
- `session_end`
- `config_update` (partial overrides)

**Server → Client**
- `transcript_chunk`, `agent_start`, `agent_done`, `tool_call`, `memory_update`, `image_generated`, `tts_chunk`, `error`, `session_status`

### Frontend (`frontend/src/`)

| Path | Role |
|---|---|
| `app/AppLayout.tsx` | Shell: Sidebar + TopBar + Outlet + MobileNav + Toaster; bootstraps WS; intercepts `tts_chunk` for audio playback |
| `store/types.ts` | `AppState`, `WSEvent` discriminated union, all interfaces |
| `store/reducer.ts` | `appReducer` dispatch table |
| `context/AppContext.tsx` | `AppProvider`, `useAppContext` hook |
| `hooks/useWebSocket.ts` | WS connection with exponential backoff (1s → 30s max); exposes `isConnected` |
| `hooks/useAudioCapture.ts` | AudioWorklet mic capture |
| `hooks/useTTSPlayer.ts` | Web Audio API TTS queue player |
| `pages/` | `SessionsPage`, `ActiveSessionPage`, `MemoryPage`, `ImagesPage`, `SettingsPage` |
| `tabs/` | `TranscriptTab`, `AgentLogTab`, `MemoryTab` (only inside `/sessions/current`) |
| `public/audio-processor.worklet.js` | AudioWorklet PCM processor |

State management: `useReducer` + Context (no Zustand). `tts_chunk` events are handled directly in `AppLayout` and piped to `useTTSPlayer` — they are NOT dispatched to the reducer.

### Frontend Stack Notes

- **Tailwind v4**: config-less. No `tailwind.config.ts`. Uses `@import "tailwindcss"` in `index.css` + `@tailwindcss/vite` plugin.
- **shadcn v4**: uses `sonner` (not `toast`) for toasts. `import { toast } from 'sonner'`.
- **Tooltip**: uses `@base-ui/react/tooltip`, not Radix. Different API — no `asChild`, uses `delay` not `delayDuration`.
- Dark mode: `class="dark"` on `<html>` in `index.html`.

### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `ELEVENLABS_API_KEY` | Yes | STT + TTS |
| `OPENAI_API_KEY` | Yes | Embeddings (`text-embedding-3-small`) |
| `ANTHROPIC_API_KEY` | Yes | Claude (Pydantic AI) |
| `APP_PASSWORD` | Optional | Password gate; disabled if unset |

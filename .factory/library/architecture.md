# Architecture

**What belongs here:** Architectural decisions, patterns discovered, component relationships.

---

## Project Structure
```
claude-code/
├── backend/          # FastAPI + Pydantic AI (Python, uv)
│   ├── main.py       # FastAPI app, REST endpoints, SPA catch-all
│   ├── ws_handler.py # WebSocket lifecycle per session
│   ├── agent.py      # Pydantic AI agent builder, tool discovery
│   ├── models.py     # Shared Pydantic models (Session, SessionConfig, etc.)
│   ├── database.py   # aiosqlite setup
│   ├── config.py     # Pydantic settings
│   ├── image_gen.py  # Pluggable image providers
│   ├── stt.py        # ElevenLabs Scribe STT
│   ├── tts.py        # ElevenLabs TTS
│   ├── memory/       # short_term.py + long_term.py
│   ├── tools/        # Auto-discovered @tool functions
│   └── tests/        # pytest tests
├── frontend/         # React + Vite + shadcn/ui (TypeScript)
│   └── src/
│       ├── app/      # AppLayout.tsx (shell + WS + TTS)
│       ├── pages/    # SessionsPage, ActiveSessionPage, SessionDetailPage, SettingsPage
│       ├── tabs/     # TranscriptTab, AgentLogTab, MemoryTab, SessionImagesTab, MainTab, LogsTab
│       ├── store/    # types.ts, reducer.ts
│       ├── context/  # AppContext.tsx (useReducer + Context)
│       ├── hooks/    # useWebSocket, useAudioCapture, useTTSPlayer
│       └── components/ # UI components
├── Dockerfile        # Multi-stage: build frontend, run backend
├── railway.toml      # Railway deploy config
└── .factory/         # Mission infrastructure
```

## Key Patterns
- **State management**: useReducer + Context (no external state lib)
- **WebSocket**: Single persistent connection per session, binary audio up, JSON events down
- **Config**: Pydantic settings on backend, localStorage on frontend, synced via session_start
- **Auth**: Optional password gate via APP_PASSWORD env var, Bearer token on REST, query param on WS
- **Database**: All tables auto-created in database.py get_db() with CREATE TABLE IF NOT EXISTS
- **Frontend build**: tsc -b && vite build, served by FastAPI catch-all in production

## CRITICAL: Never change
- ElevenLabs EU endpoints in config.py (api.eu.residency.elevenlabs.io)
- STT model scribe_v2_realtime

# User Testing

**What belongs here:** Testing surface info, tools, URLs, setup steps, isolation notes, known quirks.

---

## Testing Surface
- **Frontend**: React SPA at http://localhost:5173 (dev) or http://localhost:8000 (production build)
- **Backend API**: http://localhost:8000/api/*
- **WebSocket**: ws://localhost:8000/ws

## Testing Tools
- **OpenClaw browser**: Available, running. Use for UI validation.
  - `openclaw browser start` (already running)
  - `openclaw browser open <url>`
  - `openclaw browser snapshot` (get element refs)
  - `openclaw browser screenshot` (capture current state)
- **curl**: For API endpoint testing
- **Backend dev server**: `cd backend && uv run uvicorn main:app --reload` on port 8000
- **Frontend dev server**: `cd frontend && npm run dev` on port 5173

## Auth
- If APP_PASSWORD is set, all API calls need `Authorization: Bearer <password>` header
- WebSocket needs `?token=<password>` query param
- Check backend/.env for APP_PASSWORD value

## Known Quirks
- Frontend proxies /api and /ws to localhost:8000 in dev mode (vite.config.ts)
- TTS playback requires user gesture to resume AudioContext (browser policy)
- 4 backend tests fail due to missing OPENAI_API_KEY (pre-existing, not our concern)

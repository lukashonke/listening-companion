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

## Test Data (Seeded)
- **30 sessions total** in the database (5 original + 25 seeded test sessions named "Test Session 1" through "Test Session 25")
- **6 test images** across 3 sessions (2 images each):
  - `sess_test_401b713cf8fd` (Test Session 1): 2 images
  - `sess_test_04f9bd1afd1f` (Test Session 2): 2 images  
  - `sess_test_1550ab2f13e2` (Test Session 3): 2 images
- Images are valid 10x10 PNG files stored in `backend/images/`
- No auth required (APP_PASSWORD not set)

## Known Quirks
- Frontend proxies /api and /ws to localhost:8000 in dev mode (vite.config.ts)
- TTS playback requires user gesture to resume AudioContext (browser policy)
- 4 backend tests fail due to missing OPENAI_API_KEY (pre-existing, not our concern)

## Flow Validator Guidance: API Testing
- Base URL: `http://localhost:8000`
- No authentication headers needed
- Images API: `GET /api/images/{filename}` serves stored images
- Session images API: `GET /api/sessions/{session_id}/images` returns image metadata
- Sessions pagination API: `GET /api/sessions?offset=0&limit=20` returns `{sessions: [...], total: N}`
- Use `curl -s` for API calls, pipe to `python3 -m json.tool` for formatting
- When testing image serving, check both HTTP status code (200) and Content-Type (image/png)
- Sessions with images for testing: `sess_test_401b713cf8fd`, `sess_test_04f9bd1afd1f`, `sess_test_1550ab2f13e2`

## Flow Validator Guidance: Browser UI Testing
- Frontend URL: `http://localhost:5173`
- Use `agent-browser` skill for browser automation
- Sessions list page: `http://localhost:5173/` or `http://localhost:5173/sessions`
- Session detail page: `http://localhost:5173/sessions/{session_id}` (for past sessions)
- Active session page: `http://localhost:5173/sessions/current`
- No login required
- Browser session naming: use `--session "<worker_session_prefix>__<unique>"` format
- After each test flow, close your browser session
- Pagination: 30 sessions exist, default page size is 20, so there should be 2 pages
- Images tab in session detail: look for images section/tab when viewing a session that has images

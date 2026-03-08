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
- Pagination: 32 sessions exist (30 original + 2 smart-sessions test), default page size is 20, so there should be 2 pages
- Images tab in session detail: look for images section/tab when viewing a session that has images

## Flow Validator Guidance: Smart Sessions Testing
- **Settings page**: `http://localhost:5173/settings` — has "Background AI Features" section with Auto-Naming and Auto-Summarization controls
- **Active session page**: `http://localhost:5173/sessions/current` — has right metadata panel (SessionMetadataPanel) showing session info and summary
- **Seeded smart-sessions data**:
  - `sess_test_auto_named`: Auto-named session "Deep Discussion on AI Ethics" (name_source=auto), has summary text
  - `sess_test_user_renamed`: User-renamed session "My Custom Session Name" (name_source=user), has brief summary
- **Config fields in localStorage key `lc_config`**: auto_naming_enabled, auto_naming_first_trigger, auto_naming_repeat_interval, auto_summarization_enabled, auto_summarization_interval, auto_summarization_max_transcript_length
- **Right panel**: Only visible on active session page (not past session detail). Has data-testid attributes: session-metadata-panel, session-name, name-source-badge, session-duration, session-theme, session-summary, summary-empty-state
- **Responsive**: Right panel hidden below 768px viewport width (uses `hidden lg:flex` Tailwind classes)
- **Auto-naming and auto-summarization** require a LIVE session with real audio/transcript which we cannot fully simulate in testing. The backend logic is covered by unit tests. For user testing, verify:
  1. Settings UI exists and works (toggles, inputs, persistence)
  2. Right panel layout exists on active session page
  3. Past sessions show summaries when they have them
  4. name_source column tracks correctly in DB
  5. Sessions list shows auto-generated names
- **WebSocket session_start message**: Frontend sends config including auto_naming_* and auto_summarization_* fields when connecting to WS. This can be verified by checking the frontend code sends these fields.
- **Isolation**: Each subagent should use a unique browser session ID. No shared state issues since we're testing UI layout and settings persistence (read-only for sessions data).

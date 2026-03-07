# Bugfix Checklist

Complete all items, run tests, commit, and deploy.

## Bug 1: SPA catch-all
- [ ] In `backend/main.py`, add a catch-all GET route that serves `frontend/dist/index.html` for any path not matching `/api/*`, `/ws`, `/health`. This is standard SPA behavior — all frontend routes need to return index.html so React Router can handle them.

## Bug 2: Recording starts but nothing recorded
- [ ] Trace the `onSessionStart` callback from `TopBar.tsx` through `AppLayout.tsx` — verify it sends `{"type": "session_start", "config": {...}}` JSON over the WebSocket. If it doesn't, wire it up. The WebSocket handler in `ws_handler.py` only processes audio if a session has been started via this message.

## Bug 3: Past session detail not clickable
- [ ] In `SessionsPage.tsx`, add `onClick={() => navigate('/sessions/${session.id}')}` and `cursor-pointer hover:bg-accent/50 transition-colors` to past session `<Card>` elements.
- [ ] Create `frontend/src/pages/SessionDetailPage.tsx` — loads session data from API and displays transcript, agent log, and memory in tabs (similar to ActiveSessionPage but read-only).
- [ ] Add route `/sessions/:id` in `App.tsx` pointing to `SessionDetailPage`.
- [ ] Add `GET /api/sessions/:id` endpoint in `backend/main.py` that returns session details including transcript chunks, agent tool calls, and memory entries from the database.

## Bug 4: Logging improvements
- [ ] In `ws_handler.py`: add INFO log when `session_start` and `session_end` messages are received (with session ID). Add DEBUG log for audio chunks received (just count/size). Add INFO log for config_update applied.
- [ ] In `stt.py`: log first 50 chars of transcript text at INFO level when received.
- [ ] In `ws_handler.py` `websocket_handler`: log client connect with any available info.

## Bug 5: Password gate auth
- [ ] Add `APP_PASSWORD` to `backend/config.py` settings (default empty string = no auth).
- [ ] Add FastAPI middleware in `backend/main.py` that checks `Authorization: Bearer <password>` on all `/api/*` and `/ws` routes. Skip `/health` and static file routes. Return 401 if password is set and doesn't match.
- [ ] In frontend: detect 401 responses. Show a simple password input page/modal. Store password in `localStorage`. Send it as `Authorization: Bearer <password>` header on all fetch requests.
- [ ] For WebSocket: pass password as query param `?token=<password>` since WS doesn't support custom headers easily. Check this in the WS handler.

## Final steps
- [ ] Run `cd backend && uv lock` if deps changed
- [ ] Run `cd backend && uv run pytest` — all tests must pass
- [ ] `git add -A && git commit -m "fix: SPA routing, recording, session detail, logging, password auth"`
- [ ] `railway up --detach`
- [ ] Poll `railway deployment list` every 15s until SUCCESS or FAILED. Report final status.

# TODO Checklist — Listening Companion Fixes

## Bug Fixes

- [x] **B1: Recording should require an active session**
  - Fixed: Navigate to /sessions/current when starting recording; send session_start before starting audio (fixes ordering race)

- [x] **B2: TTS not working — nothing is recorded**
  - Fixed: ElevenLabs STT endpoint was wrong (eu.residency.elevenlabs.io → api.eu.elevenlabs.io)

## UX Improvements

- [x] **U1: Sessions should be a dedicated tab with session-scoped images**
  - Fixed: Added Images tab to ActiveSessionPage so images are scoped to the session; updated standalone /images page header to clarify context

- [x] **U2: Add "Go Back" button on the recording/transcript view**
  - Fixed: Added "Back to Sessions" button in ActiveSessionPage tab bar

- [x] **U3: Support naming and renaming sessions**
  - Fixed: Editable session name in TopBar (sent with session_start); inline rename on SessionDetailPage; backend PATCH /api/sessions/{id}

- [x] **U4: Support deleting sessions**
  - Fixed: Delete sessions with two-step confirmation on SessionsPage and SessionDetailPage; backend DELETE /api/sessions/{id} (also deletes associated memory)

## Debug & Monitoring

- [x] **D1: Add live Logs tab within the active session**
  - Add a new "Logs" tab alongside Transcript, Agent Log, Memory, Images in the active session view
  - Stream backend logs to the frontend in real-time via the existing WebSocket connection
  - Backend: send log entries as a new WS event type (e.g. `{ type: "log", level: "INFO", message: "...", timestamp: "..." }`)
  - Capture all relevant backend logs: STT connection, audio chunks received, transcript events, agent activity, TTS calls, errors
  - Frontend: display logs in a scrollable, auto-scrolling panel with color-coded log levels (ERROR=red, WARN=yellow, INFO=normal, DEBUG=gray)
  - Include a "Clear" button and optional auto-scroll toggle
  - This is critical for debugging the audio pipeline — we need to see what's happening on the backend in real-time from the browser

## After All Fixes

- [x] **Commit all changes** with a descriptive commit message — b598d03
- [x] **Deployed to Railway** — 2026-03-08

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

## Bug Fixes (Round 2)

- [x] **B3: No transcript output — Scribe receives audio but returns nothing**
  - Audio chunks reach the backend (confirmed in logs: 6400 bytes every 200ms)
  - Scribe STT connects successfully, session_started received
  - But ZERO `partial_transcript` or `committed_transcript` events come back from Scribe
  - Debug: Add INFO-level logging in `_send_loop` (confirm chunks are being sent to Scribe WS), and in `_receive_loop` (log ALL messages received from Scribe, including unknown ones)
  - Check: Is the audio format correct? Scribe expects PCM 16-bit 16kHz mono. The frontend AudioWorklet produces Int16Array at the AudioContext sample rate. Verify the sample rates match and audio_format param matches actual data.
  - Check: Is `commit` field needed? Maybe Scribe needs periodic `commit: True` or the VAD isn't triggering. Try sending a commit after silence.
  - Check: Are there any Scribe error events being silently dropped?

- [x] **B4: Tab bar not scrollable on mobile**
  - The session tabs (Transcript, Agent Log, Memory, Images, Logs) overflow on mobile screens
  - Fix: Make the tab bar horizontally scrollable on small screens (`overflow-x: auto`, hide scrollbar with CSS)
  - File: `frontend/src/pages/ActiveSessionPage.tsx` — the `tablist` element

## Configuration & Persistence

- [x] **C1: Persist settings in localStorage and expose all configurable params**
  - Currently settings are only in React state — lost on page refresh. Persist to localStorage and load on startup.
  - **Audio chunk interval**: The AudioWorklet sends chunks every 200ms (hardcoded in `audio-processor.worklet.js` as `sampleRate * 0.2`). Make this configurable from settings (e.g., 200ms, 500ms, 1000ms). This requires regenerating or parameterizing the worklet.
  - **All settings should be on the Settings page and persisted to localStorage:**
    - Voice ID (already there)
    - Agent interval (already there)
    - Image provider (already there)
    - Speaker diarization (already there)
    - Audio chunk interval (NEW — 200ms/500ms/1000ms)
    - STT language (NEW — currently hardcoded to "en", add common languages)
    - TTS model (NEW — eleven_v3 etc.)
    - Agent model (NEW — claude model override)
  - Load persisted config from localStorage on app start. Merge with defaults for any missing keys.
  - When config changes, save to localStorage immediately.

## After All Fixes

- [x] **Commit all changes** with a descriptive commit message — b598d03
- [x] **Deployed to Railway** — 2026-03-08

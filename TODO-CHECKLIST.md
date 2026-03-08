# TODO Checklist — Listening Companion Fixes

## ⚠️ CRITICAL — DO NOT CHANGE THESE
- **ElevenLabs EU endpoints** in `backend/config.py` MUST stay as:
  - `elevenlabs_eu_endpoint = "https://api.eu.residency.elevenlabs.io"`
  - `elevenlabs_stt_endpoint = "wss://api.eu.residency.elevenlabs.io"`
  - `elevenlabs_stt_model = "scribe_v2_realtime"`
  - DO NOT "fix" these — `api.eu.elevenlabs.io` does NOT exist (NXDOMAIN).

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

## Round 3 Fixes

- [x] **R1: Resume past sessions**
  - Allow continuing a past session from the Sessions list (reload transcript + memory from DB, reconnect STT)
  - Add a "Resume" button on past session cards
  - Backend: load session data from SQLite, re-initialize ActiveSession with existing transcript/memory

- [x] **R2: Cap frontend logs at 1000 entries**
  - Currently capped at 500 in LogsTab. Increase to 1000 but ensure we trim oldest entries to prevent memory overflow.

- [x] **R3: Active listening indicator in Transcript tab**
  - When recording is active, show a pulsing indicator or animated text (e.g., "🎤 Listening..." with a pulse animation) in the transcript view
  - Should be clearly distinct from the static "Start recording to see the transcript" message

- [x] **R4: TTS playback cuts off after ~0.2s**
  - Root cause: backend sent partial MP3 chunks; each was decoded as a complete audio file but only played ~0.2s
  - Fix: accumulate full MP3 bytes before emitting one on_chunk event in tts.py

- [x] **R5: Add system prompt setting to Settings page**
  - Add a textarea in Settings for custom system prompt
  - Persist to localStorage with other config
  - Send to backend via session_start config
  - Backend: custom_system_prompt appended to SYSTEM_PROMPT_TEMPLATE in agent.py

- [x] **R6: Session metadata — Name and Theme/Context**
  - Add "Session Theme" or "Context" field (e.g., "Meeting", "D&D Session", "Lecture", "Interview", "Brainstorming")
  - Persist theme in session config (stored as part of config JSON in DB)
  - Show theme on session cards in the list
  - Pass theme to the agent system prompt so it adapts its behavior

- [x] **R7: Settings page not scrollable**
  - Fixed: added overflow-y-auto wrapper to SettingsPage

- [x] **R8: OpenAI model support**
  - Add support for OpenAI models alongside Anthropic in the agent
  - Backend: model_provider + agent_model + reasoning_effort in SessionConfig; pydantic-ai OpenAI integration
  - Support: gpt-4o, gpt-4.1, gpt-4.1-mini, o3, o4-mini, o4-mini-high, o3-pro
  - Settings page: model provider dropdown, model selector, reasoning effort (o-series only)

- [x] **R9: Add Gemini model support**
  - Add Google Gemini models alongside Anthropic and OpenAI in the agent
  - Backend: use pydantic-ai's Google/Gemini model integration
  - Support latest Gemini models: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash
  - Settings page: add "Google Gemini" to model provider dropdown
  - Needs GOOGLE_API_KEY env var (or GEMINI_API_KEY) — add to config.py as optional
  - Add to Railway env vars when key is available

- [x] **R10: Add Gemini image generation support**
  - Add Google Gemini as an image provider option alongside OpenAI and fal.ai
  - Use the Gemini image generation API (Imagen via Gemini, or native Gemini image gen)
  - Models to support: gemini-2.0-flash-preview-image-generation (native multimodal image gen)
  - Settings page: add "Google Gemini" to image provider dropdown
  - Uses GOOGLE_API_KEY (same as R9)
  - API endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` with `responseModalities: ["TEXT", "IMAGE"]`

## Round 4 Fixes

- [x] **R11: Fetch OpenAI models from API instead of hardcoding**
  - Do NOT hardcode OpenAI model names — they change frequently and the hardcoded ones are already outdated
  - Backend: add an API endpoint (e.g., GET /api/models/openai) that calls the OpenAI List Models API (`GET https://api.openai.com/v1/models`) and returns available models filtered to chat/completion models (filter out embedding, whisper, tts, dall-e, moderation models)
  - Frontend: when "OpenAI" is selected as model provider, fetch available models from this endpoint and populate the dropdown dynamically
  - Cache the model list for a reasonable time (e.g., 1 hour) to avoid hitting the API on every page load
  - Sort models by name for easy browsing

## Round 5 Fixes

- [ ] **R12: Add TTS language selector (default Czech)**
  - Add a language selector to the TTS section in SettingsPage
  - The ElevenLabs TTS API accepts `language_code` in the payload — add it to the TTS request in `backend/tts.py`
  - Add `tts_language` to SessionConfig in `backend/models.py` with default `"cs"` (Czech)
  - Add `tts_language` to the frontend SessionConfig type and DEFAULT_CONFIG with default `"cs"`
  - Pass `tts_language` through from config to the TTS tool
  - Language options: cs (Czech, default), en (English), de (German), fr (French), es (Spanish), it (Italian), pt (Portuguese), ja (Japanese), zh (Chinese), pl (Polish), sk (Slovak)

- [ ] **R13: Fetch ALL model lists dynamically from APIs**
  The current hardcoded model lists are severely outdated. Fix ALL of them:

  **OpenAI models** — already has `/api/models/openai` endpoint (R11), but verify it works and the filter is good. These models MUST be available:
  - gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
  - o1, o1-pro, o3, o3-mini, o3-pro, o4-mini
  
  **Gemini models** — add a NEW backend endpoint `GET /api/models/gemini` that calls `GET https://generativelanguage.googleapis.com/v1beta/models?key=<GOOGLE_API_KEY>` and returns chat-capable Gemini models (filter out embedding, imagen, veo, gemma, aqa, robotics, tts, audio models). Must include:
  - gemini-2.0-flash, gemini-2.0-flash-lite
  - gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.5-pro
  - gemini-3-flash-preview, gemini-3-pro-preview
  - gemini-3.1-flash-lite-preview, gemini-3.1-pro-preview
  Cache for 1 hour like OpenAI endpoint.
  Frontend: when Google is selected, fetch from this endpoint.

  **Anthropic models** — Anthropic doesn't have a list models API. Keep these hardcoded but UPDATE the list:
  - claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001

  **Image generation models** — update IMAGE_PROVIDERS to include:
  - `placeholder` — Placeholder (no API)
  - `openai` — OpenAI (gpt-image-1) 
  - `gemini` — Google Gemini (gemini-2.0-flash-preview-image-generation)
  
  Also add OpenAI image generation support in `backend/image_gen.py`:
  - Use the OpenAI Images API (`POST https://api.openai.com/v1/images/generations`) with model `gpt-image-1`
  - Return the image as a data URI (base64)
  
  Remove `fal` from IMAGE_PROVIDERS since it's not implemented.

- [ ] **R14: Fix image generation tool not emitting tool_call events properly**
  Looking at the logs, the agent calls Anthropic API twice but no tool_call event appears in the Agent Log tab. Debug the `_wrap_tool` in `agent.py` — the `generate_image` tool might not be wrapping correctly, or Pydantic AI might not be calling it. 
  
  Add logging inside `generate_image` in `backend/tools/image_tool.py` to confirm whether the tool is actually invoked. Also log the provider value being used — if it's "placeholder", images won't be real.

- [ ] **R15: Add ElevenLabs voice picker dropdown**
  - Add backend endpoint `GET /api/voices/elevenlabs` that calls `GET https://api.eu.residency.elevenlabs.io/v1/voices` (with the API key) and returns `[{id, name, category}]`
  - ⚠️ Use endpoint `https://api.eu.residency.elevenlabs.io` — see CLAUDE.md for why
  - Cache for 1 hour
  - Frontend: replace the free-text voice_id input in SettingsPage with a dropdown that fetches from this endpoint
  - Show voice name + category, use voice_id as value

## Round 6 Fixes

- [ ] **R16: Add Pydantic AI model integration tests**
  Create `backend/tests/test_agent_models.py` with tests that verify ALL supported model providers work with Pydantic AI.
  
  **What to test:**
  1. Agent construction works for each provider (openai, google, anthropic) — verify `_build_agent()` returns a valid Agent
  2. Agent construction works with specific model names that users can select:
     - OpenAI: gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, gpt-5, gpt-5-mini, gpt-5.4, gpt-5.4-pro, gpt-5.3-chat-latest, o3, o4-mini
     - Google: gemini-2.5-flash, gemini-2.5-pro, gemini-3-flash-preview, gemini-3.1-flash-lite-preview, gemini-3.1-pro-preview
     - Anthropic: claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001
  3. Agent with tools can be built (pass mock tools, verify tools are registered)
  4. System prompt renders correctly with theme and custom_system_prompt
  5. Reasoning effort model settings work for OpenAI o-series models
  
  **Testing approach:**
  - Use `pytest` with `@pytest.mark.parametrize` for model matrix
  - Use `unittest.mock.patch` or `pydantic_ai.models.test.TestModel` to avoid actual API calls
  - Import from `agent.py` — test `SessionAgent._build_agent()` by creating a SessionAgent with mocked config
  - Verify the Agent object is created, has the right number of tools, etc.
  - For reasoning models (o1, o3, o4-mini), verify `OpenAIModelSettings` with `reasoning_effort` is passed
  
  **Also add:**
  - Test that `_is_chat_model()` filter in main.py correctly includes/excludes models (parametrized)
  - Test that `_is_gemini_chat_model()` filter correctly includes/excludes models (parametrized)
  
  Run tests with: `cd backend && python -m pytest tests/ -v`

## Round 7 — Agent Context & Invocation

- [ ] **R18: Improve agent context window**
  The agent currently only sees new transcripts since the last agent run. This is too limited — it has no conversation history and loses context.
  
  **Change to provide the agent with:**
  1. **Full chat history** (or a rolling window) of transcripts — not just the delta since last run. The agent should see prior conversation like a chat history so it understands the full context.
  2. **Tool call history** in an efficient form:
     - **Image generation tools:** include the full parameters (prompt, style, provider, model) so the agent knows what images were already generated and with what prompts.
     - **Memory edit tools:** only mention that they were called (e.g., "memory_update was called") — the agent can see the current memory state directly, so it doesn't need the full history of memory edits.
     - **TTS (speak) tools:** include the full text that was spoken, so the agent knows what it already said and doesn't repeat itself.
  3. Structure this as a conversation-style context the agent can reason over, not just a raw dump.

- [ ] **R19: Trigger agent on every committed transcript**
  Currently the agent runs on a timer interval (`agent_interval_s`). Change it so the agent is invoked **after every committed transcript chunk** — but only if it's not already running.
  
  - When a `committed_transcript` arrives from STT, check if the agent is currently processing. If not, trigger an agent run.
  - If the agent IS running, skip (don't queue — the next transcript will trigger it).
  - Keep the interval-based trigger as a fallback (or remove it if the transcript-based trigger is sufficient — TBD).
  - This makes the agent more responsive to the conversation flow rather than waiting for a fixed timer.

- [ ] **R20: Expose full agent system prompt in settings**
  The current "custom system prompt" field only appends to the built-in prompt. Instead, expose the **full agent system prompt** in the settings so it can be fully customized.
  
  - Add a new settings field (textarea) showing the complete system prompt template (including the built-in parts).
  - Allow the user to edit the entire prompt freely.
  - If the field is empty or reset, fall back to the built-in default prompt.
  - Persist in localStorage and send via session config like other settings.
  - Backend: use the user-provided prompt as-is (with variable substitution for `{theme}`, `{memory}`, etc.) instead of always prepending the built-in template.

## After All Fixes

- [x] **Commit all changes** with a descriptive commit message — b598d03
- [x] **Deployed to Railway** — 2026-03-08

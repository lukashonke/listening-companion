# Listening Companion App

## Overview
A general-purpose, always-listening AI companion web application. It continuously transcribes audio via ElevenLabs Scribe STT, feeds transcript chunks to a Pydantic AI agent, and the agent autonomously decides what to do using configurable tools. The app works for any scenario: D&D sessions, meetings, lectures, brainstorming, interviews — configured via tool selection.

## Architecture

### Frontend: React + Vite + shadcn/ui
- Browser captures microphone audio
- Streams audio to backend via WebSocket
- Displays: live transcript, short-term memory state, generated images, tool activity log
- Configuration UI: voice ID for TTS, session mode/tool selection, agent settings

### Backend: Python (FastAPI + WebSockets) + Pydantic AI
- Receives audio stream from frontend
- Forwards to ElevenLabs Scribe for real-time STT (WebSocket streaming)
- Accumulates transcript chunks
- Periodically invokes Pydantic AI agent with: system prompt + short-term memory + new transcript
- Agent uses tools to act on what it hears

### STT: ElevenLabs Scribe
- Always running in background while session is active
- WebSocket streaming API
- Sends continuous transcript chunks to the agent pipeline
- Speaker diarization optional (configurable)

### TTS: ElevenLabs v3 (eleven_v3)
- Used by the `answer_tts` tool when agent decides to speak
- Voice ID configurable via UI settings
- EU endpoint: https://api.eu.elevenlabs.io

### LLM: Claude via Vertex AI (Pydantic AI)
- Agent brain for all decision-making
- Called every N seconds with new transcript + short-term memory

### Image Generation: Pluggable
- Configurable provider: OpenAI (gpt-image-1), Vertex AI Imagen 3, fal.ai Flux, Together AI, Replicate
- Agent decides when to generate images based on conversation context

### Storage: SQLite
- Long-term memory storage
- Session metadata
- Simple, portable, no infrastructure needed

## Memory System

### Short-Term Memory
- Always injected into agent context on every invocation
- Each entry has a unique ID, content, and metadata
- Agent actively curates: adds, updates, removes entries
- Contains: current topic, active participants, recent key points, ongoing context
- Stored in-memory (Python dict/list), persisted to SQLite for crash recovery

### Long-Term Memory
- Persistent for the session, stored in SQLite
- NOT fed to agent by default — retrieved via semantic search
- Use SQLite with vector extension or simple embedding-based search
- Contains: full event log, decisions, quotes, archived context

### Tools

#### Core Tools (always available)
1. **save_short_term_memory(content: str, tags: list[str]) → id** — Save information to short-term memory, returns unique ID
2. **remove_short_term_memory(id: str)** — Remove a specific short-term memory entry by ID  
3. **update_short_term_memory(id: str, content: str)** — Update an existing short-term memory entry
4. **save_long_term_memory(content: str, tags: list[str])** — Archive important info to long-term storage
5. **search_long_term_memory(query: str) → list** — Semantic search over long-term memory
6. **answer_tts(text: str)** — Speak a response aloud via ElevenLabs TTS v3
7. **generate_image(prompt: str, style: str) → url** — Generate an image and display it in the UI

#### Plugin Tools (configurable per session mode)
- Extensible tool system — users can enable/disable tools per session
- Example plugins: entity tracker, action item logger, quote capture, summary generator

## Frontend UI Layout
- **Top bar:** Session name, mode selector, mic status (recording indicator), settings gear
- **Settings panel:** Voice ID, agent model, invocation frequency, enabled tools, image gen provider
- **Main area:** Live transcript (auto-scrolling) with timestamps
- **Right panel:** Short-term memory (live updated, shows IDs), generated images gallery
- **Bottom panel:** Tool activity log (what the agent did and why)

## Project Structure
See "Tech Decisions" section above for the canonical directory layout.

## Configuration
All API keys via environment variables:
- `ELEVENLABS_API_KEY` — STT (Scribe) + TTS
- `ANTHROPIC_VERTEX_PROJECT_ID` / `CLOUD_ML_REGION` — Claude via Vertex AI
- `OPENAI_API_KEY` — Image generation (if using OpenAI)
- `FAL_KEY` — Image generation (if using fal.ai)

## Tech Decisions
- Python backend with `uv` for package management
- Pydantic AI for agent framework
- FastAPI — async, WebSocket-native
- SQLite for all persistence (simple, portable)
- Semantic search: sqlite-vec or similar vector extension for SQLite
- WebSocket for all real-time communication (mic → backend, backend → frontend)
- Frontend: React + Vite + shadcn/ui (SPA, built to static files served by FastAPI)
- TypeScript frontend, Python backend; Pydantic models shared via OpenAPI → generated TS types
- Deployment: **Fly.io** — single Docker container, persistent volume for SQLite, `fly deploy`
- Monorepo structure:

```
listening-companion/
├── backend/         # FastAPI + Pydantic AI (Python, uv)
│   ├── main.py
│   ├── agent.py
│   ├── tools/
│   ├── memory/
│   ├── stt.py
│   ├── tts.py
│   ├── image_gen.py
│   └── config.py
├── frontend/        # React + Vite + shadcn/ui (TypeScript)
│   ├── src/
│   └── ...
├── Dockerfile
├── fly.toml
└── SPEC.md
```

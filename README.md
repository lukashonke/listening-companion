# Listening Companion

A real-time AI listening agent that transcribes conversations, manages memory, generates images, and speaks back via TTS. Works for any scenario: D&D sessions, meetings, lectures, brainstorming, interviews — configured via tool selection.

## Stack

- **Frontend:** React + Vite + TypeScript + shadcn/ui (dark theme)
- **Backend:** Python (uv) + FastAPI + Pydantic AI + SQLite (aiosqlite)
- **STT:** ElevenLabs Scribe (WebSocket streaming)
- **TTS:** ElevenLabs v3 (`eleven_v3`)
- **LLM:** Claude via Anthropic (Pydantic AI)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Image Gen:** Pluggable (OpenAI, Vertex Imagen, fal.ai, etc.)

## ElevenLabs EU Residency

This project uses **EU residency** endpoints:

| Service | Endpoint |
|---------|----------|
| TTS (REST) | `https://api.eu.residency.elevenlabs.io` |
| STT Scribe (WebSocket) | `wss://api.eu.residency.elevenlabs.io` |

> ⚠️ **Do NOT change these to `api.elevenlabs.io` or `api.eu.elevenlabs.io`** — the EU residency subdomain is required for EU-based API keys.

## Setup

### Backend

```bash
cd backend
uv sync
cp .env.example .env  # fill in API keys
uv run uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | ✅ | ElevenLabs API key (EU residency) |
| `OPENAI_API_KEY` | ✅ | OpenAI API key (embeddings) |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key (AI agent) |
| `APP_PASSWORD` | Optional | Password gate (disabled if unset) |

## Deployment (Railway)

```bash
railway up --detach
```

Required Railway env vars: `ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `APP_PASSWORD`

Live: https://listening-companion-production-d15c.up.railway.app

## Architecture

See [SPEC.md](SPEC.md) for full architecture details and [ARCHITECTURE.md](ARCHITECTURE.md) for component diagrams.

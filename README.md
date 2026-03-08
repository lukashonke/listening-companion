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

**Live:** https://listening-companion-production-d15c.up.railway.app

### Prerequisites

1. Install Railway CLI: `npm i -g @railway/cli`
2. Authenticate: `railway login`
3. Link to the project (run from this directory): `railway link`
   - Select the project and service when prompted

### Deploy

```bash
railway up --detach
```

This builds the Dockerfile and pushes to Railway. The `--detach` flag returns immediately without tailing logs.

### Required Environment Variables

Set via `railway variables set KEY=VALUE` or the Railway dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | ✅ | ElevenLabs API key (EU residency) |
| `OPENAI_API_KEY` | ✅ | OpenAI API key (embeddings + image gen) |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key (AI agent) |
| `GOOGLE_API_KEY` | Optional | Google API key (Gemini models + Imagen) |
| `APP_PASSWORD` | Optional | Password gate (disabled if unset) |

### Status & Logs

```bash
# List recent deployments (status, ID, time)
railway deployment list

# Tail live logs
railway logs

# Last N lines
railway logs --tail <N>

# Logs for a specific deployment
railway logs --deployment <deployment-id>

# View/list environment variables
railway variables

# Redeploy without code changes (e.g. after env var update)
railway redeploy --yes
```

> **Note:** All `railway` commands must be run from the linked project directory, or use `railway link` first.

## Architecture

See [SPEC.md](SPEC.md) for full architecture details and [ARCHITECTURE.md](ARCHITECTURE.md) for component diagrams.

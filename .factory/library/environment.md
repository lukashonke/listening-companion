# Environment

**What belongs here:** Required env vars, external API keys/services, dependency quirks, platform-specific notes.
**What does NOT belong here:** Service ports/commands (use `.factory/services.yaml`).

---

## API Keys (in backend/.env)
- `ELEVENLABS_API_KEY` - STT + TTS (EU residency endpoints)
- `OPENAI_API_KEY` - Embeddings (text-embedding-3-small) + image gen
- `ANTHROPIC_API_KEY` - Claude (Pydantic AI agent)
- `GOOGLE_API_KEY` - Optional, Gemini models
- `APP_PASSWORD` - Optional password gate

## Railway Deployment
- Persistent volume mounted at `/data/` (SQLite DB + images)
- Deploy: `railway up --detach` from project root
- Verify: `railway deployment list`
- Env vars set via Railway dashboard or `railway variables set KEY=VALUE`
- Live URL: https://listening-companion-production-d15c.up.railway.app

## Database
- SQLite via aiosqlite
- Local dev: `backend/listening_companion.db`
- Production: `/data/listening_companion.db` (env var `DATABASE_PATH`)
- Tables: sessions, short_term_memory, long_term_memory (+ new: images)

## Pre-existing Test Failures
- 4 backend tests fail due to missing OPENAI_API_KEY in test env (long-term memory embedding tests)
- These are NOT related to mission work - ignore them

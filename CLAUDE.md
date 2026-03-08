# CLAUDE.md — Project Rules

## ElevenLabs Endpoints — DO NOT CHANGE

The correct ElevenLabs EU endpoints are:

- **TTS:** `https://api.eu.residency.elevenlabs.io`
- **STT (WebSocket):** `wss://api.eu.residency.elevenlabs.io`

These are defined in `backend/config.py`. **Never change them.** The domain `api.eu.elevenlabs.io` does NOT exist (NXDOMAIN). The `residency` subdomain is the correct one.

## STT Model

The STT model is `scribe_v2_realtime`. Do not downgrade to `scribe_v1`.

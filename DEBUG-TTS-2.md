# DEBUG: STT 403 — Scribe WebSocket Rejected

## Actual Error from Railway Logs
```
2026-03-08 10:26:38,863 ws_handler INFO session_start received (new session will be: sess_fb4da7c4c26a)
2026-03-08 10:26:39,211 stt ERROR Scribe STT connection failed: server rejected WebSocket connection: HTTP 403
```

The Scribe STT WebSocket connection is getting **HTTP 403** from ElevenLabs. It retries 3 times, all fail with 403.

## What We Know
- EU residency endpoint: `wss://api.eu.residency.elevenlabs.io` — this is CORRECT, do NOT change it
- API key is passed via `xi-api-key` header
- The key is set in Railway env vars as `ELEVENLABS_API_KEY`
- `backend/config.py` reads it as `elevenlabs_api_key`

## Root Cause Investigation — Check ALL of These

1. **API key auth method**: Does ElevenLabs Scribe Realtime WebSocket accept `xi-api-key` as a header? Or does it need to be a URL query parameter? Check the ElevenLabs docs/examples. Some WebSocket implementations don't support custom headers — the key might need to go as `?xi_api_key=KEY` in the URL instead.

2. **Scribe Realtime endpoint path**: Is `/v1/speech-to-text/realtime` the correct path? Verify against ElevenLabs documentation. It might be `/v1/speech-to-text` or another path.

3. **Model ID**: Is `scribe_v1` the correct model_id parameter? Check if it should be something else.

4. **WebSocket library headers**: The `websockets` library's `connect()` with `additional_headers` — verify this actually sends custom headers during the WebSocket handshake. Some WebSocket clients don't support this properly.

5. **Test the connection**: Add a startup test or a debug endpoint that tries to connect to the Scribe WebSocket and logs the full error response (including response headers/body if available).

6. **Frontend audio**: While you're at it, verify the frontend is actually capturing and sending audio chunks over the WebSocket to the backend. Add console.logs in the frontend recording code if not already there.

## Fix Requirements
- Fix whatever is causing the 403
- Add better error logging that shows the full rejection reason
- Make sure the fix works with EU residency endpoints
- Commit with clear description of what was wrong and how you fixed it
- Do NOT stop until the fix is committed

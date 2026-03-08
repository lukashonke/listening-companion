# DEBUG: No Audio Being Sent to Backend — STT Works But Gets No Data

## Current Status
- ✅ Scribe STT connects successfully (no more 403)
- ✅ Scribe session starts: `session_started` message received from ElevenLabs
- ❌ **Zero audio chunks appear in backend logs** — no "Audio chunk received" debug messages
- ❌ No transcripts are generated
- The session lasts ~13 seconds and ends without any audio/transcript activity

## Key Logs (from Railway)
```
10:31:40,466 stt INFO Connecting to Scribe STT: wss://api.eu.residency.elevenlabs.io/v1/speech-to-text/realtime
10:31:40,868 stt INFO Scribe STT connected
10:31:40,868 stt INFO Scribe session started: {...}
10:31:40,868 ws_handler INFO Session sess_277e1a41ea90 started (tools: [])
10:31:53,284 ws_handler INFO session_end received
```
No `Audio chunk received` debug lines. No transcript. No errors.

## Architecture
1. Frontend: `useAudioCapture.ts` uses AudioWorklet (`audio-processor.worklet.js`) to capture mic → 200ms PCM chunks → `onAudioChunk` callback
2. Frontend: `TopBar.tsx` passes `onSendBinary` (which is `sendBinary` from `useWebSocket`) as the `onAudioChunk` callback
3. Frontend: `useWebSocket.ts` `sendBinary()` does `ws.send(data)` as binary WebSocket frame
4. Backend: `ws_handler.py` `websocket_handler()` checks `msg.get("bytes")` for binary frames → calls `session.handle_audio()`
5. Backend: `handle_audio()` → `ScribeSTT.send_audio()` → queues audio for ElevenLabs

## Likely Root Causes to Investigate

### Frontend Issues
1. **AudioWorklet not loading** — `/audio-processor.worklet.js` might not be served correctly in production (Railway). Check if the static file is in the built frontend dist folder and actually accessible.
2. **AudioWorklet errors** — The worklet might be failing silently. Add error handling for `addModule()`.
3. **Mic permission** — Could be silently denied (but should throw).
4. **WebSocket not ready** — The recording might start before the WS is connected. Check the timing between `onSessionStart` (which calls `sendJSON`) and `startAudio()` in `TopBar.tsx`.
5. **sendBinary never called** — The `onAudioChunk` → `sendBinary` chain might be broken. The `sendBinaryRef` pattern in `AppLayout.tsx` could have a stale closure.

### Timing Issue (MOST LIKELY)
In `TopBar.tsx handleToggleRecord()`:
```js
onSessionStart()    // sends session_start JSON
await startAudio()  // starts mic capture
```
The `startAudio()` might resolve before mic is ready, or the WS might not have received session_start acknowledgment before audio starts flowing. But the real issue is likely the opposite — audio IS flowing from the mic but the `sendBinary` callback ref is stale or not connected.

### Debug Steps
1. Add `console.log` in `useAudioCapture.ts` `onmessage` handler to verify worklet is producing audio
2. Add `console.log` in `useWebSocket.ts` `sendBinary()` to verify it's being called
3. Add `console.log` in `TopBar.tsx` to verify `startAudio()` succeeds
4. On the backend, ensure audio chunk debug logging is at INFO level (not DEBUG) so it shows in Railway logs
5. Check the built frontend dist — does it include `audio-processor.worklet.js`?

## Fix Requirements
- Find why audio chunks aren't reaching the backend
- Fix the root cause
- Ensure debug/info logging is at a level that shows in production
- Test that the full flow works: mic → worklet → WS binary → backend → Scribe → transcript
- Commit with clear description
- Do NOT change ElevenLabs endpoints — they are correct

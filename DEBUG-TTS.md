# DEBUG: TTS/STT Not Working

## CRITICAL: The EU residency endpoint was CORRECT
- The correct ElevenLabs EU residency endpoints are:
  - TTS: `https://api.eu.residency.elevenlabs.io` 
  - STT (Scribe): `wss://api.eu.residency.elevenlabs.io`
- DO NOT change these. They are correct for EU residency keys.
- If you previously changed them, revert.

## Problem
Recording starts but nothing is captured/transcribed. The user presses record and sees no transcript output. TTS (text-to-speech) also doesn't work — the AI never speaks back.

## Debug Instructions

Thoroughly trace the FULL audio pipeline end-to-end. Check EVERY step:

### Frontend (recording → sending audio)
1. Is `navigator.mediaDevices.getUserMedia()` being called correctly?
2. Is a MediaRecorder or AudioWorklet being set up properly?
3. Is the audio format correct for ElevenLabs Scribe? (PCM 16-bit, 16kHz mono expected)
4. Are audio chunks actually being sent over the WebSocket? Add console.log if missing.
5. Is the WebSocket connection established BEFORE audio starts streaming?
6. Check the WebSocket message format — does the frontend send the right message types?

### Backend (receiving audio → STT → AI → TTS)  
1. Is the WebSocket handler receiving audio data? Check logs.
2. Is the Scribe STT WebSocket connection being established to the correct endpoint?
3. Is audio data being forwarded to the Scribe WebSocket?
4. Are transcription results coming back from Scribe?
5. Is the transcript being passed to the AI agent?
6. Is the AI agent generating a response?
7. Is the TTS endpoint being called with the AI response?
8. Is the TTS audio being sent back to the frontend?
9. Is the frontend playing the received audio?

### Common Issues to Check
- WebSocket connection lifecycle (opened too late, closed too early)
- Audio format mismatch (browser sends wrong format for Scribe)
- Missing or invalid API key in deployed environment
- CORS or security headers blocking WebSocket
- session_start not being sent/received before audio streaming begins
- Error handling swallowing exceptions silently

## Output
- Fix whatever is broken
- Add proper debug logging at each stage of the pipeline if not already present
- Commit the fix with a clear description of what was wrong

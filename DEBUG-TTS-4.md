# DEBUG: Frontend Audio Pipeline — Zero Audio Chunks Reaching Backend

## Context
- Backend STT is fully working (Scribe connects, no 403, session starts)
- **ZERO audio chunks are received by the backend** when user records
- Problem is 100% on the frontend side

## Root Causes to Fix

### 1. AudioWorklet not in rendering graph (CRITICAL)
In `useAudioCapture.ts`:
```js
source.connect(workletNode)
// Do NOT connect to destination — we don't want to hear our own mic
```
The worklet node is a dead-end — not connected to `context.destination`. In many browsers, **AudioWorklet `process()` will NOT be called** if the node is not part of an active rendering path to the destination. 

**Fix:** Connect the worklet node to the destination through a GainNode with gain = 0:
```js
source.connect(workletNode)
const silentGain = context.createGain()
silentGain.gain.value = 0
workletNode.connect(silentGain)
silentGain.connect(context.destination)
```
This keeps the worklet in the rendering graph (so `process()` fires on every 128-sample block) while outputting silence.

### 2. Silent error swallowing in TopBar.tsx
In `handleToggleRecord()`:
```js
} catch {
  // mic permission denied or unavailable — stay in idle state
}
```
This silently catches ALL errors including worklet loading failures. **Fix:** Add `console.error` logging and show a toast notification so the user knows recording failed.

### 3. Missing console.log debug lines
Add `console.log` at these points for debugging:
- `useAudioCapture.ts`: When mic is acquired, when worklet loads, when first audio chunk is produced
- `useWebSocket.ts`: In `sendBinary()`, log the first few chunks being sent (with byte length)
- `TopBar.tsx`: When recording starts and stops

### 4. Verify audio-processor.worklet.js loads
The worklet loads from `/audio-processor.worklet.js`. Add error handling for `context.audioWorklet.addModule()` — if it fails (404, network error), log it clearly.

## Fix Requirements
- Fix the AudioWorklet rendering graph issue (zero-gain node to destination)
- Add proper error handling (no silent catches)
- Add console.log debug lines at key pipeline stages
- Commit with clear description
- Do NOT change ElevenLabs endpoints or backend code
- Do NOT stop until committed

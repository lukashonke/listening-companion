# TODO Checklist — Listening Companion Fixes

## Bug Fixes

- [ ] **B1: Recording should require an active session**
  - Currently you can start recording without being in a session — this is a bug.
  - Fix: The "Start Recording" button should only be available inside a session. If the user is not in a session, either prompt them to create/select one first, or auto-create a session when recording starts.

- [ ] **B2: TTS not working — nothing is recorded**
  - When starting recording, nothing is actually being captured/transcribed.
  - Debug the recording flow end-to-end: check microphone permissions, MediaRecorder setup, WebSocket connection to Scribe STT, and that audio chunks are actually being sent.
  - Check the WebSocket connection lifecycle — is it connecting to the correct endpoint? Is the session_start message being sent?

## UX Improvements

- [ ] **U1: Sessions should be a dedicated tab with session-scoped images**
  - Sessions is currently a tab — good. But when opening "Images", it's unclear which session the images belong to.
  - Fix: Images should be viewed within the context of a session (e.g., on the session detail page), OR the images view should clearly indicate which session each image belongs to.

- [ ] **U2: Add "Go Back" button on the recording/transcript view**
  - When you start recording and see the transcript, there's no way to go back.
  - Add a back/close button to return to the previous view.

- [ ] **U3: Support naming and renaming sessions**
  - Allow users to give a session a name when creating it.
  - Allow renaming an existing session (e.g., via an edit icon or context menu).
  - Backend: add a `name` field to the session model if not already present. API endpoints for create/update should accept a name.

- [ ] **U4: Support deleting sessions**
  - Add ability to delete a session (with confirmation dialog).
  - Backend: add a DELETE endpoint for sessions.
  - Frontend: add delete button/option on session list or detail page.
  - Consider: should deleting a session also delete associated transcripts, images, and memories?

## After All Fixes

- [ ] **Commit all changes** with a descriptive commit message
- [ ] Verify the app builds and runs without errors

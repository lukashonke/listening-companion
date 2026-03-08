---
name: fullstack-worker
description: Implements fullstack features spanning FastAPI backend and React frontend for the Listening Companion app
---

# Fullstack Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Use for any feature that touches both the Python/FastAPI backend and the React/TypeScript frontend. This includes new API endpoints, database schema changes, WebSocket event types, UI components, and configuration changes.

## Work Procedure

### 1. Read Context
- Read the feature description, preconditions, expectedBehavior, and verificationSteps carefully
- Read `AGENTS.md` for boundaries and conventions
- Read `.factory/library/architecture.md` for project patterns
- Read the specific backend/frontend files you'll be modifying

### 2. Plan Changes
Before writing any code, identify:
- Database schema changes needed (add to `database.py:get_db()`)
- New/modified Pydantic models (in `models.py`)
- Backend endpoint or WebSocket event changes
- Frontend state/reducer changes (types.ts, reducer.ts)
- Frontend UI component changes
- Test files to create/update

### 3. Backend First — Test-Driven
a. **Write tests first** in `backend/tests/`. Create a new test file or add to existing ones.
   - Test new endpoints with httpx AsyncClient
   - Test database operations
   - Test business logic functions
   - Run: `cd backend && uv run pytest tests/{test_file} -v` — tests should FAIL (red)

b. **Implement backend changes:**
   - Database schema: add `CREATE TABLE IF NOT EXISTS` or `ALTER TABLE` in `database.py:get_db()`
   - Models: add/update Pydantic models in `models.py`
   - Endpoints: add routes in `main.py`
   - WebSocket events: update `ws_handler.py`
   - Business logic: in appropriate module

c. **Run tests again** — they should PASS (green)
   - `cd backend && uv run pytest -x -v`

### 4. Frontend — Test-Driven
a. **Write tests first** in `frontend/src/` (co-located with component or in store/).
   - Test reducer actions for new event types
   - Test component rendering if applicable
   - Run: `cd frontend && npm run test:run` — tests should FAIL (red)

b. **Implement frontend changes:**
   - Types: add to `store/types.ts` (WSEvent union, AppState, SessionConfig)
   - Reducer: add handler in `store/reducer.ts`
   - Config defaults: update DEFAULT_CONFIG if needed
   - UI: add/modify components in pages/, tabs/, components/
   - API calls: use `apiFetch()` helper

c. **Run tests again** — they should PASS (green)
   - `cd frontend && npm run test:run`

### 5. Build & Lint Check
- `cd frontend && npm run build` (catches TypeScript errors)
- `cd frontend && npm run lint`
- `cd backend && uv run pytest -x -v` (full backend suite)

### 6. Manual Verification
For each expected behavior in the feature:
- Start the backend: `cd backend && uv run uvicorn main:app --reload`
- Start the frontend: `cd frontend && npm run dev`
- Use `openclaw browser` or `curl` to verify the behavior works
- Record what you checked and what you observed

### 7. Commit
- `git add -A && git diff --cached` (review for secrets)
- Commit with descriptive message

## Example Handoff

```json
{
  "salientSummary": "Implemented offset-based pagination for GET /api/sessions. Backend returns {sessions, total} with ?offset=&limit= params (default 20). Frontend SessionsPage shows prev/next controls with page indicator. Added 3 backend tests (pagination params, total count, empty page) and 2 frontend tests (reducer, page state).",
  "whatWasImplemented": "Backend: GET /api/sessions now accepts offset/limit query params, returns {sessions: [...], total: N}. Frontend: SessionsPage has pagination controls, dispatches page changes, shows current page / total pages.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {"command": "cd backend && uv run pytest tests/test_pagination.py -v", "exitCode": 0, "observation": "3 tests passed: test_pagination_params, test_total_count, test_empty_page"},
      {"command": "cd frontend && npm run test:run", "exitCode": 0, "observation": "16 passed (14 existing + 2 new pagination tests)"},
      {"command": "cd frontend && npm run build", "exitCode": 0, "observation": "Build succeeded, no type errors"},
      {"command": "curl 'http://localhost:8000/api/sessions?offset=0&limit=2'", "exitCode": 0, "observation": "Returned {sessions: [{...}, {...}], total: 5}"}
    ],
    "interactiveChecks": [
      {"action": "Opened SessionsPage in browser, saw 20 sessions with page controls", "observed": "Page 1 of 3 shown, Next button enabled, Prev disabled"},
      {"action": "Clicked Next, page 2 loaded", "observed": "Different sessions shown, page indicator updated to 2 of 3"},
      {"action": "Clicked Prev, returned to page 1", "observed": "Original sessions shown, Prev disabled again"}
    ]
  },
  "tests": {
    "added": [
      {"file": "backend/tests/test_pagination.py", "cases": [
        {"name": "test_pagination_params", "verifies": "offset and limit query params work correctly"},
        {"name": "test_total_count", "verifies": "total reflects actual session count"},
        {"name": "test_empty_page", "verifies": "offset beyond total returns empty sessions array"}
      ]},
      {"file": "frontend/src/store/reducer.test.ts", "cases": [
        {"name": "handles SET_PAGE action", "verifies": "page state updates correctly"},
        {"name": "resets page on new session list", "verifies": "page resets to 0 when sessions reload"}
      ]}
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Feature depends on a backend endpoint or database table that doesn't exist yet and isn't part of this feature
- The WebSocket protocol needs changes that would break other features
- Tests reveal bugs in existing code that block this feature
- The feature scope is significantly larger than described
- Cannot verify manually because dev servers won't start
- Image storage path or database path configuration is unclear for the deployment environment

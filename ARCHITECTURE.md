# Listening Companion — Architecture

> Weekend project. Keep it simple. No enterprise patterns.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER                                   │
│                                                                  │
│  Microphone ──► AudioWorklet ──► WebSocket (binary frames)      │
│                                                                  │
│  React State ◄── WebSocket (JSON events) ──────────────────┐   │
│    │                                                         │   │
│    ├── Live Transcript                                       │   │
│    ├── Short-Term Memory panel                               │   │
│    ├── Tool Activity Log                                     │   │
│    └── Image Gallery                                         │   │
└─────────────────────────────────────────────────────────────────┘
                             │ WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                               │
│                                                                  │
│  ws_handler.py                                                   │
│    │                                                             │
│    ├──► stt.py ──► ElevenLabs Scribe ──► transcript_buffer      │
│    │                    (WebSocket)                              │
│    │                                     │                      │
│    │              ┌──────────────────────┘                      │
│    │              │  every N seconds (configurable)             │
│    │              ▼                                             │
│    └──► agent.py (Pydantic AI)                                  │
│              │  system_prompt                                    │
│              │  + short_term_memory dict                        │
│              │  + new transcript chunk                          │
│              │                                                  │
│              ▼                                                  │
│         Claude (Vertex AI)                                      │
│              │                                                  │
│              ├──► tools/  (auto-discovered @tool functions)     │
│              │      ├── memory ops → memory/ module             │
│              │      ├── tts.py → ElevenLabs TTS v3              │
│              │      └── image_gen.py → pluggable providers      │
│              │                                                  │
│              └──► emits WebSocket events back to frontend       │
│                                                                  │
│  memory/                                                        │
│    ├── short_term.py  (in-memory dict, SQLite backup)           │
│    └── long_term.py   (SQLite + sqlite-vec embeddings)          │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                    ▼                    ▼
           ElevenLabs Scribe      ElevenLabs TTS
           (STT WebSocket)        (REST, EU endpoint)
```

---

## 2. WebSocket Protocol

One persistent WebSocket connection per session between browser and FastAPI backend. Audio goes up as binary frames; everything else is JSON text frames.

### Client → Server

```
Binary frame:  raw PCM audio (16kHz, 16-bit, mono) — continuous stream

Text frames (JSON):
  {"type": "session_start", "config": {
      "tools": ["entity_tracker", "quote_capture"],
      "voice_id": "JBFqnCBsd6RMkjVDRZzb",
      "agent_interval_s": 30,
      "image_provider": "fal",
      "speaker_diarization": false
  }}

  {"type": "session_end"}

  {"type": "config_update", "config": { ...partial overrides... }}
```

### Server → Client

```
  {"type": "transcript_chunk",   "text": "...", "speaker": "A", "ts": 1712345678.3}
  {"type": "agent_start",        "ts": 1712345710.0}
  {"type": "agent_done",         "ts": 1712345712.4}
  {"type": "tool_call",          "tool": "save_short_term_memory",
                                  "args": {"content": "...", "tags": ["topic"]},
                                  "result": {"id": "mem_abc123"},
                                  "ts": 1712345711.1}
  {"type": "memory_update",      "short_term": [{"id": "...", "content": "...", "tags": [...]}]}
  {"type": "image_generated",    "url": "https://...", "prompt": "...", "ts": ...}
  {"type": "tts_chunk",          "audio_b64": "...", "text": "..."}
  {"type": "error",              "code": "stt_failed", "message": "...", "fatal": false}
  {"type": "session_status",     "state": "listening" | "processing" | "idle"}
```

**Design notes:**
- Audio is forwarded straight to ElevenLabs Scribe WebSocket with minimal buffering (200ms chunks)
- TTS audio is streamed as base64 chunks; the browser decodes and plays via Web Audio API
- `memory_update` is pushed after *any* memory tool call, so the panel always stays in sync
- `fatal: true` on an error means the session has crashed and must be restarted

---

## 3. Agent Invocation Pipeline

```
transcript_buffer (list of chunks with timestamps)
        │
        │  [background task, runs every N seconds]
        ▼
┌─────────────────────────────────────────────────────┐
│  1. Drain new chunks since last invocation           │
│  2. If no new speech AND memory unchanged → skip    │
│  3. Build context:                                   │
│       system_prompt (session mode description)       │
│     + short_term_memory (full current state)         │
│     + new_transcript (joined text, with timestamps)  │
│  4. Emit "agent_start" event to frontend             │
│  5. Call Pydantic AI agent (async)                  │
│  6. Each tool call during agent run:                 │
│       a. Execute tool                                │
│       b. Emit "tool_call" event                      │
│       c. If memory changed → emit "memory_update"   │
│  7. Emit "agent_done" event                          │
│  8. Reset new-chunks buffer                          │
└─────────────────────────────────────────────────────┘
```

**Key decisions:**
- The timer is wall-clock, not transcript-event-driven. Simpler, predictable cost.
- Skip logic prevents wasted LLM calls during silence (saves ~30-40% cost in typical meetings)
- Agent invocations are serialized per session — no concurrent agent calls (avoids memory races)
- Agent has a hard timeout (default: 60s). If it exceeds this, cancel and emit an error event.
- Transcript chunks fed to agent are kept short (last N seconds only), not the full session history — that's what long-term memory is for.

---

## 4. Memory System

### Short-Term Memory (fast, always-present)

```python
# In memory, backed by SQLite for crash recovery
short_term: dict[str, MemoryEntry] = {}

@dataclass
class MemoryEntry:
    id: str          # "mem_abc123" — stable, agent references by ID
    content: str
    tags: list[str]
    created_at: float
    updated_at: float
```

- Injected into **every** agent invocation as a JSON block in the system context
- Agent controls it fully: add / update / remove via tools
- Typical contents: current topic, active participants, action items in progress, key decisions
- Persisted to SQLite on every change — if backend crashes, state is recoverable on reconnect
- Max size: soft cap at ~50 entries; if exceeded, oldest untagged entries are pruned automatically

### Long-Term Memory (searchable archive)

```
SQLite: long_term_memory table
  id          TEXT PRIMARY KEY
  session_id  TEXT
  content     TEXT
  tags        TEXT  (JSON array)
  embedding   BLOB  (float32 vector, 384-dim)
  created_at  REAL

sqlite-vec extension enables:
  SELECT content FROM long_term_memory
  WHERE session_id = ?
  ORDER BY vec_distance_cosine(embedding, ?) LIMIT 5
```

- Embeddings generated via `sentence-transformers` (all-MiniLM-L6-v2, runs locally, no API cost)
- Agent calls `search_long_term_memory(query)` when it needs historical context
- `save_long_term_memory` is a deliberate act — the agent decides what's worth archiving
- Sessions can optionally load long-term memory from previous sessions (cross-session recall)

---

## 5. Plugin / Tool System

> Write a function, drop it in `tools/`, it shows up. That's the whole system.

### The @tool Decorator

```python
# tools/entity_tracker.py
from api.tools import tool

@tool(tags=["plugin"])
def track_entity(name: str, entity_type: str, description: str) -> str:
    """
    Track a named entity mentioned in the conversation (person, place, item, concept).
    Call whenever a significant new entity is introduced.
    """
    # implementation
    return f"Tracking {entity_type}: {name}"
```

### Auto-Discovery

On startup, `agent.py` scans `tools/` and collects all `@tool`-decorated functions:

```python
# agent.py  (~15 lines, no magic)
import importlib, pkgutil, pathlib

def discover_tools() -> dict[str, callable]:
    tools_dir = pathlib.Path(__file__).parent / "tools"
    for _, module_name, _ in pkgutil.iter_modules([str(tools_dir)]):
        importlib.import_module(f"api.tools.{module_name}")
    return _TOOL_REGISTRY   # populated by @tool decorator

# The registry is just a module-level dict
_TOOL_REGISTRY: dict[str, callable] = {}

def tool(fn=None, *, tags=None):
    def decorator(f):
        _TOOL_REGISTRY[f.__name__] = f
        f._tool_tags = tags or []
        return f
    return decorator(fn) if fn else decorator
```

### Session-Level Filtering

The session config contains `"tools": ["entity_tracker", "quote_capture"]`. The agent is built with only those functions, plus the always-on core tools:

```python
CORE_TOOLS = ["save_short_term_memory", "remove_short_term_memory",
              "update_short_term_memory", "save_long_term_memory",
              "search_long_term_memory", "answer_tts", "generate_image"]

active_tools = [_TOOL_REGISTRY[name]
                for name in (CORE_TOOLS + session_config.tools)
                if name in _TOOL_REGISTRY]

agent = Agent(model, tools=active_tools, system_prompt=...)
```

### What Counts as a Tool

- A Python function in `tools/` with `@tool`
- Type-annotated parameters (Pydantic AI uses these for the JSON schema)
- Docstring = tool description for the LLM
- Return a string or dict
- Can use session context via a simple `get_session_context()` helper (injected via closure at agent-build time)

### What Is NOT a Tool

- Abstract base classes, interfaces, plugin manifests, registration files
- Dynamic loading at runtime after startup
- Versioning, hot-reload — restart the server to pick up new tools

---

## 6. Frontend State Management (React + Vite + shadcn/ui)

All UI state derives from WebSocket events. No polling, no REST for real-time data.

```typescript
// Single useWebSocket hook owns the connection and dispatches to state

type AppState = {
  sessionStatus: "idle" | "listening" | "processing"
  transcript: TranscriptChunk[]        // append-only, auto-scroll
  shortTermMemory: MemoryEntry[]        // replaced wholesale on memory_update
  toolLog: ToolEvent[]                  // append-only ring buffer (last 100)
  images: GeneratedImage[]             // append-only
  isAgentThinking: boolean             // true between agent_start / agent_done
  error: AppError | null
}

// WebSocket dispatch table — one handler per event type
const handlers: Record<string, (state: AppState, msg: any) => AppState> = {
  transcript_chunk:  (s, m) => ({ ...s, transcript: [...s.transcript, m] }),
  memory_update:     (s, m) => ({ ...s, shortTermMemory: m.short_term }),
  tool_call:         (s, m) => ({ ...s, toolLog: [...s.toolLog.slice(-99), m] }),
  image_generated:   (s, m) => ({ ...s, images: [...s.images, m] }),
  agent_start:       (s)    => ({ ...s, isAgentThinking: true }),
  agent_done:        (s)    => ({ ...s, isAgentThinking: false }),
  session_status:    (s, m) => ({ ...s, sessionStatus: m.state }),
  error:             (s, m) => ({ ...s, error: m }),
}
```

**Notes:**
- Use `useReducer` with the dispatch table, not a pile of `useState` calls
- Audio capture lives in a separate `useAudioCapture` hook; it only sends binary frames over the socket
- TTS audio received as `tts_chunk` events is piped to the Web Audio API in a tiny `useTTSPlayer` hook
- Reconnect logic: exponential backoff (1s → 2s → 4s → max 30s), session resumes automatically
- No state persistence in the browser — page refresh = clean slate (session state lives on backend)

---

## 7. Error Handling Strategy

The guiding principle: **the listening session must never crash due to a single failure**. Degrade gracefully, log everything.

| Layer | Failure | Response |
|---|---|---|
| Audio / WebSocket | Browser tab loses focus, network hiccup | Frontend auto-reconnects with backoff; backend keeps STT alive for 10s before closing |
| STT (Scribe) | ElevenLabs WebSocket drops | Reconnect, re-send session start; emit non-fatal error; resume accumulating transcript |
| Agent invocation | LLM timeout / API error | Skip this cycle, log to tool_log, retry next interval |
| Tool call | Tool function throws | Pydantic AI catches exception, returns error string to agent so it can decide to retry or move on; emit tool_call event with `"error": "..."` |
| Memory | SQLite write fails | Log warning, keep going (in-memory state is source of truth; SQLite is backup) |
| TTS | ElevenLabs TTS fails | Emit error event to UI, session continues listening |
| Image gen | Provider API fails | Return error to agent, agent can try different prompt or skip |
| Config | Unknown tool name in session config | Skip silently, log warning at startup |

**Frontend errors:**
- Non-fatal: display in a dismissible toast
- Fatal (`error.fatal: true`): show persistent banner, offer "Restart Session"
- Lost WebSocket while recording: show reconnecting spinner over the mic indicator

---

## 8. Token Cost Estimates per Hour

Assumptions: Claude Sonnet 3.7 pricing (~$3/M input, $15/M output), 30-second agent intervals, moderate meeting pace (~120 words/min speech).

### Per Invocation (30-second window)

| Component | Tokens |
|---|---|
| System prompt + instructions | ~500 |
| Short-term memory (10 entries avg) | ~400 |
| Transcript chunk (30s ≈ 60 words) | ~100 |
| **Total input** | **~1,000** |
| Agent response + tool calls | ~200 |

### Per Hour

| Metric | Value |
|---|---|
| Invocations | 120 |
| Input tokens | 120K |
| Output tokens | 24K |
| Claude input cost | $0.36 |
| Claude output cost | $0.36 |
| **Claude subtotal** | **~$0.72/hr** |

### Other Services

| Service | Est. cost/hr |
|---|---|
| ElevenLabs Scribe STT | ~$0.40 (audio hours pricing) |
| ElevenLabs TTS (if agent speaks ~5×/hr, ~100 chars each) | ~$0.03 |
| Image generation (fal.ai Flux, if 3 images/hr) | ~$0.03 |
| **Total all-in** | **~$1.15/hr** |

### Levers to Reduce Cost
- **60s intervals instead of 30s** → Claude cost drops to ~$0.40/hr total
- **Skip invocation during silence** (implemented) → saves ~30% on typical meetings
- **Trim short-term memory** to <30 entries → saves ~200 tokens/call
- **Use Claude Haiku** for lightweight sessions → 10× cheaper, less reasoning quality

> At 30-second intervals with a 2-hour session: ~$2.30 total. Very affordable.

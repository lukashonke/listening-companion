from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
import time
import uuid


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def now() -> float:
    return time.time()


# ── Session ──────────────────────────────────────────────────────────────────

class SessionConfig(BaseModel):
    tools: list[str] = []
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    agent_interval_s: int = 30
    image_provider: str = "placeholder"
    speaker_diarization: bool = False


class Session(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sess_"))
    name: str = ""
    created_at: float = Field(default_factory=now)
    ended_at: float | None = None
    config: SessionConfig = Field(default_factory=SessionConfig)


# ── Memory ────────────────────────────────────────────────────────────────────

class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mem_"))
    content: str
    tags: list[str] = []
    created_at: float = Field(default_factory=now)
    updated_at: float = Field(default_factory=now)


class LongTermEntry(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ltm_"))
    session_id: str
    content: str
    tags: list[str] = []
    created_at: float = Field(default_factory=now)


# ── Transcript ────────────────────────────────────────────────────────────────

class TranscriptChunk(BaseModel):
    text: str
    speaker: str = "A"
    ts: float = Field(default_factory=now)


# ── WebSocket event types ─────────────────────────────────────────────────────

class WsTranscriptChunk(BaseModel):
    type: Literal["transcript_chunk"] = "transcript_chunk"
    text: str
    speaker: str
    ts: float


class WsAgentStart(BaseModel):
    type: Literal["agent_start"] = "agent_start"
    ts: float = Field(default_factory=now)


class WsAgentDone(BaseModel):
    type: Literal["agent_done"] = "agent_done"
    ts: float = Field(default_factory=now)


class WsToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool: str
    args: dict
    result: dict | str | None = None
    error: str | None = None
    ts: float = Field(default_factory=now)


class WsMemoryUpdate(BaseModel):
    type: Literal["memory_update"] = "memory_update"
    short_term: list[MemoryEntry]


class WsImageGenerated(BaseModel):
    type: Literal["image_generated"] = "image_generated"
    url: str
    prompt: str
    ts: float = Field(default_factory=now)


class WsTtsChunk(BaseModel):
    type: Literal["tts_chunk"] = "tts_chunk"
    audio_b64: str
    text: str


class WsError(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    fatal: bool = False


class WsSessionStatus(BaseModel):
    type: Literal["session_status"] = "session_status"
    state: Literal["listening", "processing", "idle"]


# ── Client → Server frames ────────────────────────────────────────────────────

class WsSessionStart(BaseModel):
    type: Literal["session_start"]
    config: SessionConfig = Field(default_factory=SessionConfig)


class WsSessionEnd(BaseModel):
    type: Literal["session_end"]


class WsConfigUpdate(BaseModel):
    type: Literal["config_update"]
    config: dict

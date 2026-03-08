import time
from models import MemoryEntry, SessionConfig, TranscriptChunk, new_id, now


def test_new_id_prefix():
    id_ = new_id("mem_")
    assert id_.startswith("mem_")
    assert len(id_) == 16  # "mem_" (4) + 12 hex chars


def test_new_id_no_prefix():
    id_ = new_id()
    assert len(id_) == 12


def test_memory_entry_defaults():
    entry = MemoryEntry(content="test content")
    assert entry.id.startswith("mem_")
    assert entry.tags == []
    assert entry.created_at <= time.time()
    assert entry.updated_at <= time.time()


def test_session_config_defaults():
    config = SessionConfig()
    assert config.agent_interval_s == 30
    assert config.image_provider == "gemini"
    assert config.tools == []
    assert config.speaker_diarization is False


def test_transcript_chunk_defaults():
    chunk = TranscriptChunk(text="hello world")
    assert chunk.speaker == "A"
    assert chunk.ts <= time.time()


def test_ws_events_serialize():
    from models import WsTranscriptChunk, WsMemoryUpdate, WsError
    chunk = WsTranscriptChunk(text="hello", speaker="A", ts=1.0)
    data = chunk.model_dump_json()
    assert '"type":"transcript_chunk"' in data

    err = WsError(code="test", message="oops")
    assert err.fatal is False
    data = err.model_dump_json()
    assert '"type":"error"' in data

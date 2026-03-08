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


def test_session_config_auto_naming_defaults():
    config = SessionConfig()
    assert config.auto_naming_enabled is True
    assert config.auto_naming_first_trigger == 5
    assert config.auto_naming_repeat_interval == 10


def test_session_config_auto_summarization_defaults():
    config = SessionConfig()
    assert config.auto_summarization_enabled is True
    assert config.auto_summarization_interval == 300
    assert config.auto_summarization_max_transcript_length == 50000


def test_session_config_accepts_custom_background_llm_settings():
    config = SessionConfig(
        auto_naming_enabled=False,
        auto_naming_first_trigger=10,
        auto_naming_repeat_interval=20,
        auto_summarization_enabled=False,
        auto_summarization_interval=600,
        auto_summarization_max_transcript_length=100000,
    )
    assert config.auto_naming_enabled is False
    assert config.auto_naming_first_trigger == 10
    assert config.auto_naming_repeat_interval == 20
    assert config.auto_summarization_enabled is False
    assert config.auto_summarization_interval == 600
    assert config.auto_summarization_max_transcript_length == 100000


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

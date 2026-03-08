from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_tts_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_tts_model: str = "eleven_v3"
    elevenlabs_eu_endpoint: str = "https://api.eu.elevenlabs.io"
    elevenlabs_stt_model: str = "scribe_v1"
    elevenlabs_stt_endpoint: str = "wss://api.eu.elevenlabs.io"

    # OpenAI
    openai_api_key: str = ""

    # Google / Gemini
    google_api_key: str = ""

    # Anthropic / Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"

    # Agent
    agent_interval_s: int = 30
    agent_timeout_s: int = 60
    agent_transcript_window_s: int = 120

    # Memory
    short_term_memory_max: int = 50
    long_term_embedding_dim: int = 384

    # Database
    database_path: str = "listening_companion.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_dist: str = "../frontend/dist"

    # Auth (empty = no auth)
    app_password: str = ""


settings = Settings()

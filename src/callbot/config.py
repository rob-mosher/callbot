"""Environment-driven settings. Everything tunable lives here."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM — local, on the subnet.
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b"

    # STT — cloud.
    deepgram_api_key: str = ""

    # TTS voice. Kokoro requires one explicitly; 54 are available.
    kokoro_voice: str = "af_heart"

    # Telephony.
    daily_api_key: str = ""
    daily_caller_id: str = ""
    principal_number: str = ""

    # Behavior.
    bot_name: str = "Ash"
    principal_name: str = "the principal"
    min_seconds_before_bridge: int = 15
    max_call_seconds: int = 900
    principal_answer_timeout: int = 45
    retain_transcripts: bool = False


settings = Settings()

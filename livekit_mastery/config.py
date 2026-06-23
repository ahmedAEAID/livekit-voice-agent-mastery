"""Environment configuration shared by all lessons."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env.local"

# LiveKit's worker CLI reads its connection settings before a room job creates
# an AgentSession. Load the local environment as soon as the shared package is
# imported so `agents.cli.run_app(...)` can discover LIVEKIT_URL and credentials.
load_dotenv(DEFAULT_ENV_FILE)


class ConfigurationError(RuntimeError):
    """Raised when a lesson is missing required environment variables."""


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    stt_base_url: str
    stt_api_key: str
    stt_model: str
    xtts_base_url: str
    xtts_voice: str
    xtts_language: str = "en"

    @classmethod
    def from_env(cls, env_file: Path = DEFAULT_ENV_FILE) -> Settings:
        load_dotenv(env_file)
        env_mapping = {
            "livekit_url": "LIVEKIT_URL",
            "livekit_api_key": "LIVEKIT_API_KEY",
            "livekit_api_secret": "LIVEKIT_API_SECRET",
            "llm_base_url": "OPENAI_BASE_URL",
            "llm_api_key": "OPENAI_API_KEY",
            "llm_model": "MODEL_NAME_LLM",
            "stt_base_url": "STT_BASE_URL",
            "stt_api_key": "STT_API_KEY",
            "stt_model": "STT_MODEL_ID",
            "xtts_base_url": "XTTS_BASE_URL",
            "xtts_voice": "VOICE_WAV_NAME",
            "xtts_language": "XTTS_LANGUAGE",
        }
        values = {field: os.getenv(env_name) for field, env_name in env_mapping.items()}
        values["xtts_language"] = values["xtts_language"] or "en"
        missing = [env_mapping[field] for field, value in values.items() if not value]
        if missing:
            raise ConfigurationError(f"Missing required configuration: {', '.join(missing)}")
        return cls(**values)  # type: ignore[arg-type]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and validate `.env.local` once per worker process."""

    return Settings.from_env()

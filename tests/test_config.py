from pathlib import Path

import pytest

from livekit_mastery.config import DEFAULT_ENV_FILE, ConfigurationError, Settings

REQUIRED_ENV = {
    "LIVEKIT_URL": "wss://example.livekit.cloud",
    "LIVEKIT_API_KEY": "key",
    "LIVEKIT_API_SECRET": "secret",
    "OPENAI_BASE_URL": "https://llm.example/v1",
    "OPENAI_API_KEY": "llm-key",
    "MODEL_NAME_LLM": "example-llm",
    "STT_BASE_URL": "https://stt.example/v1",
    "STT_API_KEY": "stt-key",
    "STT_MODEL_ID": "example-stt",
    "XTTS_BASE_URL": "http://xtts.example:8044",
    "VOICE_WAV_NAME": "female.wav",
}


def test_default_environment_file_points_to_project_root() -> None:
    assert DEFAULT_ENV_FILE.name == ".env.local"
    assert (DEFAULT_ENV_FILE.parent / "pyproject.toml").exists()


def test_settings_load_required_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("XTTS_LANGUAGE", raising=False)

    settings = Settings.from_env(Path("/nonexistent"))

    assert settings.llm_model == "example-llm"
    assert settings.xtts_language == "en"


def test_settings_report_real_environment_name(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("STT_API_KEY")

    with pytest.raises(ConfigurationError, match="STT_API_KEY"):
        Settings.from_env(Path("/nonexistent"))

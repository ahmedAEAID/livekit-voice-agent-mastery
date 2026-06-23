"""Factory for the STT -> LLM -> TTS pipeline used throughout the course."""

from __future__ import annotations

from typing import Any

from livekit.agents import AgentSession
from livekit.plugins import openai, silero

from .config import Settings, get_settings
from .xtts import CustomXTTS


def create_session(
    *,
    settings: Settings | None = None,
    vad: Any | None = None,
    userdata: Any | None = None,
    language: str | None = None,
    **session_options: Any,
) -> AgentSession:
    """Create the course's default OpenAI-compatible STT/LLM and XTTS session."""

    cfg = settings or get_settings()
    options: dict[str, Any] = {
        "stt": openai.STT(
            model=cfg.stt_model,
            api_key=cfg.stt_api_key,
            base_url=cfg.stt_base_url,
        ),
        "llm": openai.LLM(
            model=cfg.llm_model,
            api_key=cfg.llm_api_key,
            base_url=cfg.llm_base_url,
        ),
        "tts": CustomXTTS(
            server_url=cfg.xtts_base_url,
            speaker_wav=cfg.xtts_voice,
            language=language or cfg.xtts_language,
        ),
        "vad": vad or silero.VAD.load(),
    }
    if userdata is not None:
        options["userdata"] = userdata
    options.update(session_options)
    return AgentSession(**options)

"""Lesson 6: test and evaluate agent behavior without audio.

LiveKit's `AgentSession` can drive an agent in text-only mode and let you assert
on the resulting events. Paired with an LLM judge, this turns fuzzy questions
("did it greet politely?", "did it call the right tool?") into repeatable tests.

Run (needs the LLM credentials from your .env.local):
    uv run pytest 06_testing_and_evals/eval_assistant.py -v

These evals call a real LLM, so they are intentionally excluded from the default
`uv run pytest` run (see `testpaths` in pyproject.toml). If credentials are
missing, each test skips instead of failing.
"""

from __future__ import annotations

import pytest
from livekit.agents import Agent, AgentSession, function_tool
from livekit.plugins import openai

from livekit_mastery.config import ConfigurationError, get_settings


def _build_llm() -> openai.LLM:
    """Build an OpenAI-compatible LLM from the shared configuration."""

    cfg = get_settings()
    return openai.LLM(
        model=cfg.llm_model,
        api_key=cfg.llm_api_key,
        base_url=cfg.llm_base_url,
    )


@pytest.fixture
def llm() -> openai.LLM:
    """Provide an LLM for both the agent and the judge, or skip without keys."""

    try:
        return _build_llm()
    except ConfigurationError as exc:
        pytest.skip(f"LLM credentials are not configured: {exc}")


class WeatherAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a concise weather assistant. Greet the user briefly. "
                "When asked about the weather somewhere, call the get_weather tool "
                "and report the result in one short sentence."
            )
        )

    @function_tool
    async def get_weather(self, location: str) -> str:
        """Return the current weather for a location."""

        return f"It is 22 degrees and sunny in {location}."


@pytest.mark.asyncio
async def test_greets_and_offers_help(llm: openai.LLM) -> None:
    # Arrange
    async with AgentSession(llm=llm) as session:
        await session.start(WeatherAssistant())

        # Act
        result = await session.run(user_input="Hi there")

        # Assert: the first reply is an assistant message that reads as a greeting.
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(llm, intent="A brief, friendly greeting that offers help")
        )


@pytest.mark.asyncio
async def test_calls_weather_tool(llm: openai.LLM) -> None:
    # Arrange
    async with AgentSession(llm=llm) as session:
        await session.start(WeatherAssistant())

        # Act
        result = await session.run(user_input="What's the weather in Cairo?")

        # Assert: the agent decided to call get_weather rather than guessing.
        result.expect.contains_function_call(name="get_weather")

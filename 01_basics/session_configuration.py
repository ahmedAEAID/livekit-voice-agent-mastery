"""Lesson 3: tune interruptions, endpointing, and usage metrics."""

import logging

from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    MetricsCollectedEvent,
    function_tool,
    metrics,
    room_io,
)

from livekit_mastery import create_session

# Set up simple logging
logger = logging.getLogger("voice-agent")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You have a specific tool to check the weather; use it immediately when asked about weather conditions.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis.
            You are curious, friendly, and have a sense of humor.""",
        )

    # --- 2. FIXED TOOL DEFINITION ---
    @function_tool
    async def get_weather(self, location: str) -> str:
        """
        Called when the user asks about the weather.

        Args:
            location: The location to get the weather for
        """
        logger.info(f"🌤️ Tool Called: Weather for {location}")
        return f"The weather in {location} is sunny and 25 degrees Celsius."


server = AgentServer()


@server.rtc_session(agent_name="standard_agent")
async def my_agent(ctx: agents.JobContext):
    session = create_session(
        user_away_timeout=30.0,
        # --- Turn Detection & Interruption Settings ---
        allow_interruptions=True,  # Allow the user to cut off the agent mid-sentence.
        discard_audio_if_uninterruptible=True,  # Ignore user audio if interruptions are turned off.
        min_interruption_duration=0.5,  # Require 0.5 seconds of user speech to trigger an interruption.
        min_interruption_words=0,  # Minimum words needed to interrupt (0 means any speech counts).
        # 1. Endpointing (When does the user's turn end?)
        min_endpointing_delay=0.5,
        # The standard wait time (0.5s) of silence to consider the user's turn complete.
        # Since we use standard VAD (not a smart Turn Detector), this is the delay that actually applies.
        max_endpointing_delay=3.0,
        # Max wait time (3.0s) if the system thinks the user is just pausing mid-sentence.
        # NOTE: This has NO effect here because it requires an advanced Turn Detector model to work.
        # 2. False Interruptions (Handling background noise vs. actual speech)
        false_interruption_timeout=2.0,
        # Waits 2.0s to see if the STT model actually outputs transcribed text from the detected noise.
        # If no text is generated, it's flagged as a "false interruption". (Set to None to disable this check).
        resume_false_interruption=True,
        # If the interruption was deemed false (i.e., just a cough or background noise with no STT text),
        # the agent will automatically resume speaking from the exact point it was cut off.
    )

    # Initialize UsageCollector
    usage_collector = metrics.UsageCollector()

    # --- EVENT LISTENERS ---
    @session.on("metrics_collected")
    def on_metrics_collected(event: MetricsCollectedEvent):
        """
        Triggered whenever a component (STT, LLM, TTS) reports performance data.
        """
        # 1. Collect data for the final summary
        metrics.log_metrics(event.metrics)
        usage_collector.collect(event.metrics)

        # 2. Real-time Analysis
        # We access metrics via the 'metrics' module we imported

        # A. LLM Usage
        if isinstance(event.metrics, metrics.LLMMetrics):
            logger.info(
                f"💰 LLM Cost: {event.metrics.prompt_tokens} prompt + {event.metrics.completion_tokens} completion tokens."
            )

        # B. TTS Latency
        elif isinstance(event.metrics, metrics.TTSMetrics):
            logger.info(f"⚡ TTS Speed: {event.metrics.ttfb}ms to first byte.")

        elif isinstance(event.metrics, metrics.STTMetrics):
            logger.debug("🎤 STT Activity detected.")

    # 3. Log the full session summary when the agent shuts down
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"📊 Session Summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # --- START SESSION ---
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=room_io.RoomOptions(),
    )

    await session.generate_reply(instructions="Greet the user.")


if __name__ == "__main__":
    agents.cli.run_app(server)

"""Lesson 7: collect usage metrics and log a session summary.

Every component in the pipeline (STT, LLM, TTS, VAD, end-of-utterance) emits
metrics through the session's `metrics_collected` event. Aggregate them with a
`UsageCollector` and log a single summary when the job shuts down — this is the
foundation for cost tracking and production observability.

Run:
    uv run 07_observability/usage_metrics_agent.py dev
"""

import logging

from livekit import agents
from livekit.agents import Agent, AgentServer, metrics
from livekit.agents.metrics import UsageCollector

from livekit_mastery import create_session

logger = logging.getLogger("observability")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful, concise voice assistant.",
        )


server = AgentServer()


@server.rtc_session(agent_name="observability_agent")
async def entrypoint(ctx: agents.JobContext) -> None:
    session = create_session()
    usage = UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(ev: agents.MetricsCollectedEvent) -> None:
        # Pretty-print each component's metrics as they arrive...
        metrics.log_metrics(ev.metrics)
        # ...and feed them into the aggregator for the end-of-session summary.
        usage.collect(ev.metrics)

    async def _log_usage_summary() -> None:
        summary = usage.get_summary()
        logger.info("Session usage summary: %s", summary)

    # Shutdown callbacks run once the job ends, so the summary reflects the
    # entire conversation.
    ctx.add_shutdown_callback(_log_usage_summary)

    await session.start(room=ctx.room, agent=Assistant())
    await session.generate_reply(instructions="Greet the user and offer your assistance.")


if __name__ == "__main__":
    agents.cli.run_app(server)

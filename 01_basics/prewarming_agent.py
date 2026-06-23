"""Lesson 2: prewarm the local VAD model to reduce cold-start latency.

Run:
    uv run 01_basics/prewarming_agent.py dev
"""

from livekit.agents import (
    Agent,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import silero

from livekit_mastery import create_session


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a expert engineering assistant in programming and software development. You eagerly assist users with their questions by providing information from your extensive knowledge."""
        )


async def entrypoint(ctx: JobContext):
    session = create_session(vad=ctx.proc.userdata["vad"])

    await session.start(room=ctx.room, agent=Assistant())
    await session.generate_reply(instructions="Greet the user and offer your assistance.")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="prewarming_agent",
            port=8082,
            prometheus_port=9001,
        )
    )

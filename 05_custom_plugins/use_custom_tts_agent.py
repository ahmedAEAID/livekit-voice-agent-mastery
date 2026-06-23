"""Lesson: use the shared XTTS adapter in a complete voice session."""

import logging

from livekit import agents
from livekit.agents import Agent, AgentServer, room_io

from livekit_mastery import create_session

logger = logging.getLogger("xtts-test")
logger.setLevel(logging.INFO)


class BasicTestAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful assistant. Keep your answers very short (1-2 sentences max) to test voice synthesis. Respond in Arabic."
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Say a short greeting in Arabic welcoming the user and telling them you are ready to test the voice."
        )


server = AgentServer()


@server.rtc_session(agent_name="xtts_tester")
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()
    session = create_session()

    logger.info("Starting Agent Session...")
    await session.start(
        room=ctx.room,
        agent=BasicTestAgent(),
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    agents.cli.run_app(server)

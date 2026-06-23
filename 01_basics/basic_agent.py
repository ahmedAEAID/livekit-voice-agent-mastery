"""Lesson 1: build the smallest useful voice agent.

Run:
    uv run 01_basics/basic_agent.py dev
"""

from livekit import agents
from livekit.agents import Agent, AgentServer, room_io

from livekit_mastery import create_session


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )


server = AgentServer()


@server.rtc_session(agent_name="standard_agent")
async def my_agent(ctx: agents.JobContext):
    session = create_session()

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=room_io.RoomOptions(
            # audio_input=room_io.AudioInputOptions(
            #     noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
            # ),
        ),
    )

    await session.generate_reply(instructions="Greet the user and offer your assistance.")


if __name__ == "__main__":
    agents.cli.run_app(server)

import asyncio
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import (
    JobContext,
    JobProcess,
    WorkerOptions,
    AgentSession,
    Agent,
    room_io,
    cli
)
from livekit.plugins import silero

load_dotenv(".env.local")

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a expert engineering assistant in programming and software development. You eagerly assist users with their questions by providing information from your extensive knowledge."""
        )

async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="deepgram/nova-3:multi",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"], 
    )

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
import logging
import os
from dotenv import load_dotenv
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, room_io
from livekit.plugins import silero, openai

from custom_xtts_plugin.xtts import CustomXTTS

load_dotenv(".env.local")
logger = logging.getLogger("xtts-test")
logger.setLevel(logging.INFO)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME_LLM = os.getenv('MODEL_NAME_LLM')
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
STT_BASE_URL=os.getenv("STT_BASE_URL")
STT_MODEL_ID=os.getenv("STT_MODEL_ID")
STT_API_KEY=os.getenv("STT_API_KEY")
XTTS_BASE_URL=os.getenv("XTTS_BASE_URL")
VOICE_WAV_NAME=os.getenv("VOICE_WAV_NAME")
XTTS_LANGUAGE=os.getenv("XTTS_LANGUAGE")

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
    
    logger.info("Setting up XTTS...")
    my_xtts = CustomXTTS(
        server_url=XTTS_BASE_URL,
        speaker_wav=VOICE_WAV_NAME,
        language=XTTS_LANGUAGE
    )

    # تهيئة الجلسة (Session)
    session = AgentSession(
        stt=openai.STT(
            model=STT_MODEL_ID,
            api_key=STT_API_KEY,
            base_url=STT_BASE_URL
        ),
        llm=openai.LLM(
            model=MODEL_NAME_LLM,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        ),
        tts=my_xtts, 
        vad=silero.VAD.load(),
    )
    
    logger.info("Starting Agent Session...")
    await session.start(
        room=ctx.room,
        agent=BasicTestAgent(),
        room_options=room_io.RoomOptions(),
    )

if __name__ == "__main__":
    agents.cli.run_app(server)
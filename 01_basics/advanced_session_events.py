import logging
import asyncio
from dotenv import load_dotenv
import pathlib

from livekit import agents, rtc
from livekit.agents import (
    AgentServer, AgentSession, Agent, room_io, 
    FunctionToolsExecutedEvent, metrics, MetricsCollectedEvent, ErrorEvent,CloseEvent,
    function_tool # <--- 1. Import function_tool here
)
from livekit.rtc import ParticipantKind
from livekit.agents.utils.audio import audio_frames_from_file

from livekit.agents import llm
from livekit.plugins import noise_cancellation, silero, openai, cartesia
import os

load_dotenv(".env.local")

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
    # Initialize Session
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MODEL_NAME_LLM = os.getenv('MODEL_NAME_LLM')
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    STT_BASE_URL=os.getenv("STT_BASE_URL")
    STT_MODEL_ID=os.getenv("STT_MODEL_ID")
    STT_API_KEY=os.getenv("STT_API_KEY")
    
    TTS_BASE_URL=os.getenv("TTS_BASE_URL")
    TTS_MODEL_ID=os.getenv("TTS_MODEL_ID")
    TTS_API_KEY=os.getenv("TTS_API_KEY")
    
    session = AgentSession(
        stt=openai.STT(model=STT_MODEL_ID,
                       api_key=STT_API_KEY,
                       base_url=STT_BASE_URL),
        llm=openai.LLM(model=MODEL_NAME_LLM,
                       api_key=OPENAI_API_KEY,
                       base_url=OPENAI_BASE_URL),
        tts=cartesia.TTS(model=TTS_MODEL_ID,
                     voice="f786b574-daa5-4673-aa0c-cbe3e8534c02",
                     api_key=TTS_API_KEY),
        vad=silero.VAD.load(),
        user_away_timeout=30.0 
    )

    # Initialize UsageCollector
    usage_collector = metrics.UsageCollector()

    # --- EVENT LISTENERS ---

    

    @session.on("function_tools_executed")
    def on_function_tools_executed(event: FunctionToolsExecutedEvent):
        for call, output in event.zipped():
            # Note: We use call.name and output.output based on previous fixes
            result = output.output if output else "No output"
            logger.info(f"🛠️ Tool Executed: {call.name} -> {result}")

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
            logger.info(f"💰 LLM Cost: {event.metrics.prompt_tokens} prompt + {event.metrics.completion_tokens} completion tokens.")

        # B. TTS Latency
        elif isinstance(event.metrics, metrics.TTSMetrics):
            logger.info(f"⚡ TTS Speed: {event.metrics.ttfb}ms to first byte.")
            
        elif isinstance(event.metrics, metrics.STTMetrics):
             logger.debug(f"🎤 STT Activity detected.")

    # 3. Log the full session summary when the agent shuts down
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"📊 Session Summary: {summary}")

    ctx.add_shutdown_callback(log_usage)
    
    custom_error_audio = os.path.join(pathlib.Path(__file__).parent.absolute(), "error_message.ogg")
    
    # @session.on("error")
    # def on_error(ev: ErrorEvent):
    #     """
    #     Triggered when an error occurs during the session.
    #     Logs the source of the error, the error details, and the model configuration.
    #     """
    #     # Identify which component caused the error (e.g., STT, LLM, TTS)
    #     source_name = type(ev.source).__name__ if ev.source else "Unknown Component"
    #     error_type = type(ev.error).__name__

    #     # 1. Handle Recoverable Errors (The system will retry)
    #     if ev.error.recoverable:
    #         logger.warning(f"⚠️ Recoverable {error_type} in {source_name}: {ev.error}")
    #         # Debug level is good here so it doesn't clutter your main logs unless needed
    #         logger.debug(f"⚙️ Model Config: {ev.model_config}")
    #         return

    #     # 2. Handle Unrecoverable Errors (The system exhausted retries or cannot recover)
    #     logger.error(f"🚨 UNRECOVERABLE ERROR in {source_name} 🚨")
    #     logger.error(f"   -> Error Detail: {ev.error}")
    #     logger.error(f"   -> Model Config: {ev.model_config}")
    #     logger.error("Session is closing due to this unrecoverable error.")

    #     # To bypass the TTS service in case it's unavailable, we use a custom audio file instead
    #     session.say(
    #         "I'm having trouble connecting right now. Let me transfer your call.",
    #         audio=audio_frames_from_file(custom_error_audio),
    #         allow_interruptions=False,
    #     )
    @session.on("error")
    def on_error(ev: ErrorEvent):
        # if ev.error.recoverable:
        #     return

        logger.info(f"session is closing due to unrecoverable error {ev.error}, {custom_error_audio}")

        # To bypass the TTS service in case it's unavailable, we use a custom audio file instead
        session.say(
            "I'm having trouble connecting right now. Let me transfer your call.",
            audio=audio_frames_from_file(custom_error_audio),
            allow_interruptions=False,
        )
        logger.error(f"🚨 UNRECOVERABLE ERROR: {ev.error}")
    
    
    
    # --- START SESSION ---
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=room_io.RoomOptions(),
    )

    # await session.generate_reply(instructions="Greet the user.")
    bad_instruction = "Greet the user. " * 50000
    await session.generate_reply(instructions=bad_instruction)

if __name__ == "__main__":
    agents.cli.run_app(server)

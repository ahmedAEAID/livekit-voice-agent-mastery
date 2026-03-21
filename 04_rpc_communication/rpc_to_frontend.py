import logging
import asyncio
from dotenv import load_dotenv
import pathlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

from livekit import agents, rtc
from livekit.agents import (
    AgentServer, AgentSession, Agent, room_io, 
    FunctionToolsExecutedEvent, metrics, MetricsCollectedEvent, ErrorEvent,CloseEvent,
    function_tool # <--- 1. Import function_tool here
)
from livekit.agents import JobContext, WorkerOptions, cli, Agent, AgentSession, inference, RunContext, function_tool

from livekit.agents import llm
from livekit.plugins import noise_cancellation, silero, openai, cartesia
import os

load_dotenv(".env.local")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME_LLM = os.getenv('MODEL_NAME_LLM')
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
STT_BASE_URL=os.getenv("STT_BASE_URL")
STT_MODEL_ID=os.getenv("STT_MODEL_ID")
STT_API_KEY=os.getenv("STT_API_KEY")

TTS_BASE_URL=os.getenv("TTS_BASE_URL")
TTS_MODEL_ID=os.getenv("TTS_MODEL_ID")
TTS_API_KEY=os.getenv("TTS_API_KEY")

# Set up simple logging
logger = logging.getLogger("voice-agent")



@dataclass
class UserSessionData:
    data_objects: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    room: Optional[rtc.Room] = None
    remote_participants_identities: list = field(default_factory=list)

class RPCStateAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
                You are a professional and helpful voice assistant. 
                
                CRITICAL INSTRUCTION:
                You have a tool called 'confirm_action'. You MUST use this tool whenever the user needs to make a choice or confirm an action on their screen. 
                
                When you call the 'confirm_action' tool:
                1. State clearly what you are asking for.
                2. Wait for the tool to return the user's response ('yes' or 'no').
                3. Do not proceed with the action until you receive a 'yes'.
                
                STYLE:
                - Be concise and to the point.
                - Do not use emojis, complex punctuation, or special characters in your speech.
                - Maintain a friendly, curious, and slightly humorous personality.
            """,
        )
    
    @function_tool
    async def confirm_action(self, context: RunContext[UserSessionData], message: str) -> str:
        """
        A tool to confirm an action with the user on their screen.
        """
        if not context.userdata.remote_participants_identities:
            return "Error: No user found to confirm with."
            
        participant_identity = context.userdata.remote_participants_identities[0]
        
        try:
            logger.info(f"⏳ Calling RPC 'show_confirmation' for: {participant_identity}")
            
            response = await context.userdata.room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="show_confirmation", 
                payload=message, 
                response_timeout=15.0 
            )
            
            logger.info(f"✅ User responded: {response}")
            return f"The user selected: {response}"
            
        except Exception as e:
            logger.error(f"❌ RPC Failed or Timeout: {e}")
            return "The user did not respond in time."
    

server = AgentServer()

@server.rtc_session(agent_name="standard_agent")
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()
    # Initialize Session
    
    userdata = UserSessionData()
    
    session = AgentSession[UserSessionData](
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
        user_away_timeout=30.0,
        userdata=userdata,
    )
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant {participant.identity} joined")
    userdata.room = ctx.room  # Store the room in userdata for later use
    userdata.remote_participants_identities.append(participant.identity)
    # Initialize UsageCollector
    usage_collector = metrics.UsageCollector()
    
    

    # --- EVENT LISTENERS ---
    @session.on("metrics_collected")
    def on_metrics_collected(event: MetricsCollectedEvent):
        metrics.log_metrics(event.metrics)
        usage_collector.collect(event.metrics)
        if isinstance(event.metrics, metrics.LLMMetrics):
            logger.info(f"💰 LLM Cost: {event.metrics.prompt_tokens} prompt + {event.metrics.completion_tokens} completion tokens.")
        elif isinstance(event.metrics, metrics.TTSMetrics):
            logger.info(f"⚡ TTS Speed: {event.metrics.ttfb}ms to first byte.")
        elif isinstance(event.metrics, metrics.STTMetrics):
             logger.debug(f"🎤 STT Activity detected.")

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"📊 Session Summary: {summary}")

    ctx.add_shutdown_callback(log_usage)
    
    
    
    
    # --- START SESSION ---
    await session.start(
        room=ctx.room,
        agent=RPCStateAgent(),
        room_options=room_io.RoomOptions(),
    )

    # await session.generate_reply(instructions="Greet the user.")
    instruction = "Greet the user. "
    await session.generate_reply(instructions=instruction)

if __name__ == "__main__":
    agents.cli.run_app(server)

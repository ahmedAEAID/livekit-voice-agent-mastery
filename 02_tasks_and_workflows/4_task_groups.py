import logging
import asyncio
from dotenv import load_dotenv
import pathlib
import os

from livekit import api, agents, rtc
from livekit.agents import (
    AgentServer, AgentSession, Agent, room_io, 
    FunctionToolsExecutedEvent, metrics, MetricsCollectedEvent, 
    function_tool, AgentTask, get_job_context
)
from livekit.agents.beta.workflows import TaskGroup
from livekit.agents.utils.audio import audio_frames_from_file
from dataclasses import dataclass
from livekit.plugins import silero, openai, cartesia, cambai
from livekit.agents.beta.tools import EndCallTool

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

plugins_dir = os.path.join(parent_dir, "05_custom_plugins")
sys.path.append(plugins_dir)

from custom_xtts_plugin.xtts import CustomXTTS

load_dotenv(".env.local")
# Set up logging
logger = logging.getLogger("agent-group-tasks")

STT_BASE_URL=os.getenv("STT_BASE_URL")
STT_MODEL_ID=os.getenv("STT_MODEL_ID")
STT_API_KEY=os.getenv("STT_API_KEY")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME_LLM = os.getenv('MODEL_NAME_LLM')
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

XTTS_BASE_URL= os.getenv("XTTS_BASE_URL")
XTTS_LANGUAGE=os.getenv("XTTS_LANGUAGE")
VOICE_WAV_NAME=os.getenv("VOICE_WAV_NAME")

@dataclass
class IntroResults:
    name: str 
    intro: str

@dataclass
class CommuteResults:
    commute_can: bool
    commute_method: str

class IntroTask(AgentTask[IntroResults]):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
            Your goal is to get the user's name and a brief introduction in 1-2 sentences.
            Ask for the user's name first, then ask them to introduce themselves.
            """,
            chat_ctx=chat_ctx,
        )
        
        self._results = {}

    async def on_enter(self) -> None:
        # This is the first thing the user hears when the task starts
        await self.session.generate_reply(
            instructions="Hi! Let's start with your name. What should I call you?"
        )

    @function_tool
    async def record_name(self, name: str):
        """Record the user's name."""
        logger.info(f"👤 Name recorded: {name}")
        self._results["name"] = name
        self._check_completion()
        
        return f"Nice to meet you, {name}!"
    
    @function_tool
    async def record_intro(self, intro: str):
        """Record the user's introduction."""
        logger.info(f"📝 Introduction recorded: {intro}")
        self._results["intro"] = intro
        self._check_completion()
        
        return "Thanks for the introduction!"
    def _check_completion(self):
        if self._results.keys() == {"name", "intro"}:
            self.complete(IntroResults(name=self._results["name"], intro=self._results["intro"]))
        

class CommuteTask(AgentTask[CommuteResults]):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
            Your goal is to find out if the user can commute to an office and how they would do it.
            First ask if they are able to commute to an office. If they say yes, ask how they would commute (e.g. car, public transit).
            """,
             chat_ctx=chat_ctx,
         )
        self._results = {}

    async def on_enter(self) -> None:
        # This is the first thing the user hears when the task starts
        await self.session.generate_reply(
            instructions="hello welcome to the company! I have a quick question about your commute. Are you able to commute to our office location if needed?"
        )

    @function_tool
    async def record_commute_can(self, can_commute: bool):
        """Record whether the user can commute."""
        logger.info(f"🚗 Can commute: {can_commute}")
        self._results["commute_can"] = can_commute
        self._check_completion()
        if can_commute:
            return "Great! How would you typically commute (e.g. car, public transit)?"
        else:
            return "No worries! Remote work is also an option."

    @function_tool
    async def record_commute_method(self, method: str):
        """Record the user's commute method."""
        logger.info(f"🚌 Commute method recorded: {method}")
        self._results["commute_method"] = method
        self._check_completion()
        return "Thanks for sharing your commute method!"
    
    def _check_completion(self):
        if self._results.get("commute_can") == False:
            self.complete(CommuteResults(commute_can=False, commute_method=""))
        elif self._results.keys() == {"commute_can", "commute_method"}:
            self.complete(CommuteResults(commute_can=True, commute_method=self._results["commute_method"]))

class HiringAgent(Agent):
    def __init__(self):
        end_call_tool = EndCallTool(
            extra_description="Only end the call after confirming the customer's issue is resolved.",
            delete_room=True,
            end_instructions="Thank the customer for their time and wish them a good day.",
        )
        super().__init__(instructions="You are a professional hiring coordinator.", tools=end_call_tool.tools,)

    async def on_enter(self) -> None:
        # Create the Group
        task_group = TaskGroup()
        
        task_group.add(
            lambda: IntroTask(chat_ctx=self.chat_ctx),
            id="intro",
            description="Collecting name and self-intro"
        )
        task_group.add(
            lambda: CommuteTask(chat_ctx=self.chat_ctx),
            id="commute",
            description="Checking commute availability"
        )

        # Execute and wait for ALL steps to finish
        logger.info("🚀 Starting Hiring Workflow...")
        group_results = await task_group
        
        # Access data from specific tasks
        intro_data: IntroResults = group_results.task_results["intro"]
        commute_data: CommuteResults = group_results.task_results["commute"]

        logger.info(f"✅ Workflow Complete: {intro_data.name} | Commute: {commute_data.commute_can}")

        # Final goodbye using the collected data
        await self.session.generate_reply(
            instructions=f"Thank {intro_data.name} for the info. Let them know the team will review their profile."
        )

server = AgentServer()

@server.rtc_session(agent_name="hiring_agent")
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
    usage_collector = metrics.UsageCollector()
    
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

    logger.info("Starting Agent Session...")
    await session.start(
        room=ctx.room,
        agent=HiringAgent(),
        room_options=room_io.RoomOptions(),
    )
    
if __name__ == "__main__":
    agents.cli.run_app(server)
    
        

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
from livekit.agents.utils.audio import audio_frames_from_file
from dataclasses import dataclass
from livekit.plugins import silero, openai, cartesia, cambai

load_dotenv(".env.local")

# Set up logging
logger = logging.getLogger("agent-task")

class CollectConsent(AgentTask[bool]):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
            Your only goal is to ask for recording consent. 
            Do not answer any other questions until you have a clear 'Yes' or 'No'.
            If the user is unsure, explain it is for quality assurance.
            """,
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        # This is the first thing the user hears when the task starts
        await self.session.generate_reply(
            instructions="""
            Introduce yourself as the AI assistant and ask if it is okay to record 
            this conversation for training purposes.
            """
        )

    @function_tool
    async def consent_given(self) -> None:
        """Call this tool only when the user explicitly says yes or agrees to recording."""
        logger.info("✅ Consent granted by user.")
        self.complete(True)

    @function_tool
    async def consent_denied(self) -> None:
        """Call this tool only when the user explicitly says no or refuses recording."""
        logger.info("❌ Consent denied by user.")
        self.complete(False)
        
@dataclass
class ContactInfoResult:
    name: str
    email_address: str
    phone_number: str

class GetContactInfoTask(AgentTask[ContactInfoResult]):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
            Your goal is to collect the user's full name, email address, and phone number.
            Ask for them one by one if necessary to be clear.
            Once you have all three pieces of information, call the submit_contact_info tool.
            """,
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        # Start the conversation for this specific task
        await self.session.generate_reply(
            instructions="Greeting the user and explain you need their contact details to proceed."
        )

    @function_tool
    async def submit_contact_info(
        self, 
        name: str, 
        email: str, 
        phone: str
    ) -> None:
        """Call this tool only when you have collected all three: name, email, and phone."""
        logger.info(f"💾 Saving Contact Info: {name}, {email}, {phone}")
        
        # Create the result object and complete the task
        result = ContactInfoResult(
            name=name, 
            email_address=email, 
            phone_number=phone
        )
        self.complete(result)
        

class CustomerServiceAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a friendly customer service representative.")

    async def on_enter(self) -> None:
        # Step 1: Ask for Consent
        consent_task = CollectConsent(chat_ctx=self.chat_ctx)
        has_consent = await consent_task

        if not has_consent:
            await self.session.generate_reply(instructions="Explain you must end the call without consent.")
            await asyncio.sleep(5)
            get_job_context().shutdown()
            return

        # Step 2: Get Contact Info (The new Task)
        contact_task = GetContactInfoTask(chat_ctx=self.chat_ctx)
        contact_info = await contact_task # Wait for the dataclass result

        # Step 3: Success! Use the collected data
        logger.info(f"Final Data Collected: {contact_info}")
        await self.session.generate_reply(
            instructions=f"Thank {contact_info.name} for providing their email {contact_info.email_address}. Ask how else you can help."
        )

server = AgentServer()

@server.rtc_session(agent_name="customer_support")
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()
    
    session = AgentSession(
        stt=openai.STT(
            model=os.getenv("STT_MODEL_ID"),
            api_key=os.getenv("STT_API_KEY"),
            base_url=os.getenv("STT_BASE_URL")
        ),
        llm=openai.LLM(
            model=os.getenv("MODEL_NAME_LLM"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        ),
        # tts=cartesia.TTS(
        #     model=os.getenv("TTS_MODEL_ID"),
        #     voice="f786b574-daa5-4673-aa0c-cbe3e8534c02",
        #     api_key=os.getenv("TTS_API_KEY")
        # ),
        tts = cambai.TTS(
            model="mars-flash",
            voice_id=147320,
        ),
        vad=silero.VAD.load(),
        user_away_timeout=30.0 
    )
    
    usage_collector = metrics.UsageCollector()
    @session.on("function_tools_executed")
    def on_function_tools_executed(event: FunctionToolsExecutedEvent):
        for call, output in event.zipped():
            # You can see which tool was called across any active task
            result = output.output if output else "No output"
            logger.info(f"🛠️ Tool: {call.name} | Result: {result}")

    @session.on("metrics_collected")
    def on_metrics_collected(event: MetricsCollectedEvent):
        metrics.log_metrics(event.metrics)
        usage_collector.collect(event.metrics)

    # Start session with the Main Agent
    await session.start(
        room=ctx.room,
        agent=CustomerServiceAgent(),
    )
    
if __name__ == "__main__":
    agents.cli.run_app(server)
"""Lesson: gate a conversation behind an explicit consent task."""

import asyncio
import logging

from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentTask,
    MetricsCollectedEvent,
    function_tool,
    get_job_context,
    metrics,
)

from livekit_mastery import create_session

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


class CustomerServiceAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a friendly customer service representative.")

    async def on_enter(self) -> None:
        # The Agent starts by running the CollectConsent task
        consent_task = CollectConsent(chat_ctx=self.chat_ctx)
        result = await consent_task
        logger.info(f"Consent result: {result}")

        if result:
            # If consent is True, continue the normal conversation
            await self.session.generate_reply(
                instructions="The user agreed. Thank them and ask how you can help today."
            )
        else:
            # If consent is False, say goodbye and terminate the call
            await self.session.generate_reply(
                instructions="The user refused. Politely explain you cannot proceed without recording and say goodbye."
            )

            # Wait a few seconds for the audio to finish before hanging up
            await asyncio.sleep(5)
            job_ctx = get_job_context()
            # await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))
            job_ctx.shutdown()


server = AgentServer()


@server.rtc_session(agent_name="customer_support")
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()

    session = create_session(user_away_timeout=30.0)

    usage_collector = metrics.UsageCollector()

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

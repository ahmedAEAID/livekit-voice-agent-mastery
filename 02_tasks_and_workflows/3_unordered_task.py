"""Lesson: collect structured fields in any conversational order."""

import asyncio
import logging
from dataclasses import dataclass

from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentTask,
    FunctionToolsExecutedEvent,
    MetricsCollectedEvent,
    function_tool,
    get_job_context,
    metrics,
    room_io,
)

from livekit_mastery import create_session

logger = logging.getLogger("behavioral-task")


@dataclass
class BehavioralResults:
    strengths: str
    weaknesses: str
    work_style: str


class BehavioralTask(AgentTask[BehavioralResults]):
    def __init__(self, chat_ctx=None) -> None:
        super().__init__(
            instructions="""
            Conduct a professional interview to collect strengths, weaknesses, and work style.
            The user can answer these in any order. 
            Confirm each piece of information as you receive it.
            Do not finish until you have all three pieces.
            """,
            chat_ctx=chat_ctx,
        )
        self._results = {}

    async def on_enter(self) -> None:
        # Initial greeting to set the stage
        await self.session.generate_reply(
            instructions="Introduce yourself as an interviewer and ask the candidate to talk about themselves."
        )

    @function_tool()
    async def record_strengths(self, strengths_summary: str):
        """Record candidate's strengths based on their answer."""
        logger.info(f"💪 Strengths recorded: {strengths_summary}")
        self._results["strengths"] = strengths_summary
        self._check_completion()
        return "Strengths noted."

    @function_tool()
    async def record_weaknesses(self, weaknesses_summary: str):
        """Record candidate's weaknesses based on their answer."""
        logger.info(f"⚠️ Weaknesses recorded: {weaknesses_summary}")
        self._results["weaknesses"] = weaknesses_summary
        self._check_completion()
        return "Weaknesses noted."

    @function_tool()
    async def record_work_style(self, work_style: str):
        """Record candidate's work style (e.g. remote, collaborative)."""
        logger.info(f"💼 Work style recorded: {work_style}")
        self._results["work_style"] = work_style
        self._check_completion()
        return "Work style noted."

    def _check_completion(self):
        required_keys = {"strengths", "weaknesses", "work_style"}
        if self._results.keys() == required_keys:
            # All fields collected, finish the task
            results = BehavioralResults(
                strengths=self._results["strengths"],
                weaknesses=self._results["weaknesses"],
                work_style=self._results["work_style"],
            )
            logger.info("✅ All interview data collected. Task complete.")
            self.complete(results)
        else:
            # Some fields missing, prompt the user for the rest
            missing = required_keys - self._results.keys()
            self.session.generate_reply(
                instructions=f"Acknowledge what you heard, then ask about the remaining: {', '.join(missing)}."
            )


class InterviewerAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are an expert HR interviewer.")

    async def on_enter(self) -> None:
        # Start the specialized behavioral task
        task = BehavioralTask(chat_ctx=self.chat_ctx)
        final_results = await task

        # After task completes, use the structured data
        logger.info(f"Final Interview Summary: {final_results}")
        await self.session.generate_reply(
            instructions="""
            1. Thank the candidate for the interview. 
            2. Summarize their strengths, weaknesses, and work style.
            """
        )

    @function_tool
    async def end_call(self) -> None:
        """Ends the conversation and hangs up the call."""
        logger.info("Hanging up the call...")

        await self.session.generate_reply(
            instructions="Thank the candidate for the interview. and say goodbye."
        )

        # Brief delay to ensure the last TTS sentence is heard by the user
        await asyncio.sleep(2)

        job_ctx = get_job_context()
        job_ctx.shutdown()


server = AgentServer()


@server.rtc_session(agent_name="interviewer_agent")
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()

    # Initialize the session
    session = create_session(user_away_timeout=30.0)

    usage_collector = metrics.UsageCollector()

    # --- EVENT LISTENERS ---
    @session.on("function_tools_executed")
    def on_function_tools_executed(event: FunctionToolsExecutedEvent):
        for call, output in event.zipped():
            result = output.output if output else "No output"
            logger.info(f"🛠️ Tool Executed: {call.name} -> {result}")

    @session.on("metrics_collected")
    def on_metrics_collected(event: MetricsCollectedEvent):
        metrics.log_metrics(event.metrics)
        usage_collector.collect(event.metrics)

        if isinstance(event.metrics, metrics.LLMMetrics):
            logger.info(
                f"💰 LLM Cost: {event.metrics.prompt_tokens} prompt + {event.metrics.completion_tokens} completion tokens."
            )
        elif isinstance(event.metrics, metrics.TTSMetrics):
            logger.info(f"⚡ TTS Speed: {event.metrics.ttfb}ms to first byte.")
        elif isinstance(event.metrics, metrics.STTMetrics):
            logger.debug("🎤 STT Activity detected.")

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"📊 Session Summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session with the initial agent
    await session.start(
        room=ctx.room,
        agent=InterviewerAgent(),
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    agents.cli.run_app(server)

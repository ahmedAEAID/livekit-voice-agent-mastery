import logging
from dataclasses import dataclass, field
from typing import Any

from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    MetricsCollectedEvent,
    RunContext,
    function_tool,
    metrics,
    room_io,
)

from livekit_mastery import create_session

# Set up simple logging
logger = logging.getLogger("voice-agent")


@dataclass
class UserSessionData:
    data_objects: dict[str, dict[str, Any]] = field(default_factory=dict)
    room: rtc.Room | None = None
    remote_participants_identities: list[str] = field(default_factory=list)


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
        if context.userdata.room is None or not context.userdata.remote_participants_identities:
            return "Error: No user found to confirm with."

        participant_identity = context.userdata.remote_participants_identities[0]

        try:
            logger.info(f"⏳ Calling RPC 'show_confirmation' for: {participant_identity}")

            response = await context.userdata.room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="show_confirmation",
                payload=message,
                response_timeout=15.0,
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

    session = create_session(
        user_away_timeout=30.0,
        userdata=userdata,
    )
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant {participant.identity} joined")
    userdata.room = ctx.room  # Store the room in userdata for later use
    userdata.remote_participants_identities.append(participant.identity)

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(disconnected: rtc.RemoteParticipant):
        if disconnected.identity in userdata.remote_participants_identities:
            userdata.remote_participants_identities.remove(disconnected.identity)

    # Initialize UsageCollector
    usage_collector = metrics.UsageCollector()

    # --- EVENT LISTENERS ---
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

import logging
import asyncio
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, ConversationItemAddedEvent, UserStateChangedEvent, function_tool, FunctionToolsExecutedEvent, CloseEvent
from livekit.plugins import noise_cancellation, silero
from livekit.agents.voice import UserInputTranscribedEvent
from livekit.agents.llm import ImageContent, AudioContent

load_dotenv(".env.local")

# Set up simple logging
logger = logging.getLogger("voice-agent")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )
    @function_tool
    async def get_weather(self, location: str) -> str:
        """
        Called when the user asks about the weather.

        Args:
            location: The location to get the weather for
        """
        return f"The weather in {location} is sunny today."

server = AgentServer()

@server.rtc_session(agent_name="standard_agent")
async def my_agent(ctx: agents.JobContext):
    # 1. Initialize Session with Timeout Configuration
    session = AgentSession(
        stt="deepgram/nova-3:multi",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=silero.VAD.load(),
        user_away_timeout=10.0  # <--- CHANGED: Set timeout to 30 seconds
    )
    inactivity_task: asyncio.Task | None = None
    # --- EVENT LISTENERS (Must be defined BEFORE session.start) ---

    @session.on("agent_state_changed")
    def on_agent_state_changed(event):
        # Convert enum to string for comparison if needed, or use .name
        new_state = str(event.new_state)
        old_state = str(event.old_state)

        if new_state == "thinking":
            logger.info(f"🤔 Agent Thinking. (Previous: {old_state})")
            # Useful for: Triggering a 'processing' animation or 'hmmm' filler sound
            
        elif new_state == "speaking":
            logger.info(f"🗣️ Agent Speaking. (Previous: {old_state})")
            # Useful for: Lowering background music volume (ducking), showing agent waveform
            
        elif new_state == "listening":
            logger.info(f"👂 Agent Listening. (Previous: {old_state})")
            # Useful for: Resuming background music, highlighting user microphone UI
            
            
    async def user_presence_task():
        # try to ping the user 3 times, if we get no answer, close the session
        for _ in range(3):
            await session.generate_reply(
                instructions=(
                    "The user has been inactive. Politely check if the user is still present."
                )
            )
            await asyncio.sleep(10)

        session.shutdown()

    @session.on("user_state_changed")
    def on_user_state_changed(event: UserStateChangedEvent):
        nonlocal inactivity_task
        new_state = str(event.new_state)
        old_state = str(event.old_state)
        

        # 1. User started speaking (Interrupt)
        if new_state == "speaking":
            logger.info(f"🎤 User Speaking. (Previous: {old_state})")
            # Useful for: Cancelling current Agent speech (interruption), visually highlighting user avatar
            
        # 2. User stopped speaking (Silence detected)
        elif new_state == "listening":
            logger.info(f"🤫 User Silent/Listening. (Previous: {old_state})")
            # Useful for: Detecting end of turn, preparing to send audio to LLM

        # 3. User is Away (Timeout hit)
        elif new_state == "away":
            logger.warning(f"⚠️ User Away. (No input for 30s)")
            # Useful for: Disconnecting the session to save costs, or prompting: "Are you still there?"
            # session.generate_reply(
            #     instructions="The user has been silent for a while. Gently ask them 'Are you still there?' to check on them."
            # )
            inactivity_task = asyncio.create_task(user_presence_task())
            return
        if inactivity_task is not None :
            inactivity_task.cancel()
    
        
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        """
        Triggered when the STT model converts user speech to text.
        """
        # Check if the sentence is complete (Final result)
        if event.is_final:
            logger.info(f"📝 Final Transcript: '{event.transcript}' (Lang: {event.language})")
            
            # Useful for:
            # 1. Logging conversations to a database for analytics.
            # 2. Triggering keyword commands (e.g., if user says "Stop", kill the job immediately).
            # 3. Performing sentiment analysis on the user's text.

            # Example: Keyword spotting logic
            if "stop" in event.transcript.lower():
                logger.info("🛑 User said STOP. Ending session...")

        # If the result is interim (User is still speaking)
        else:
            # logger.debug(f"✍️ Interim: '{event.transcript}'")
            pass
            
            # Useful for:
            # 1. Showing real-time captions (Subtitles) on the frontend UI.
            # 2. Detecting interruption intent early (faster than waiting for VAD silence).
    
    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        """
        Triggered when a message is officially committed to the chat history 
        (both User and Agent messages).
        """
        item = event.item
        role = item.role # "user" or "assistant"
        text = item.text_content
        
        # Log the history item based on who said it
        if role == "user":
            logger.info(f"💾 HISTORY [User]: {text}")
        elif role == "assistant":
            # Check if the agent was interrupted
            status = " (Interrupted)" if item.interrupted else ""
            logger.info(f"💾 HISTORY [Agent]: {text}{status}")

        # Useful for:
        # 1. Database Storage: This is the perfect place to save the conversation 
        #    to your database (SQL/MongoDB) because it captures the final context.
        # 2. Chat UI Sync: Sending this data to the frontend to display the 
        #    chat bubble history.
        # 3. Analytics: Tracking how often the agent is interrupted by the user.
        
    @session.on("function_tools_executed")
    def on_function_tools_executed(event: FunctionToolsExecutedEvent):
        """
        Triggered when the agent finishes executing a tool/function.
        """
        # 1. Log the global event flags
        logger.info(f"🔧 Tool Event Flags: Reply Required={event.has_tool_reply}, Handoff Required={event.has_agent_handoff}")

        # Useful for:
        # 1. Silent Execution: You can call `event.cancel_tool_reply()` here if you want the 
        #    agent to stay silent after running a tool (e.g., logging data in the background).
        # 2. Flow Control: Checking `has_agent_handoff` lets you know if the user is being 
        #    transferred to another agent.

        # 2. Loop through the executed tools
        for call, output in event.zipped():
            function_name = call.name 
            arguments = call.arguments
            
            # --- FIX: Use .output instead of .content ---
            result = output.output if output else "No output" 

            logger.info(f"🛠️ Tool Executed: {function_name}")
            logger.info(f"   - Args: {arguments}")
            logger.info(f"   - Result: {result}")

            # Useful for:
            # 1. Debugging: Verify exactly what arguments the LLM sent to your API.
            # 2. Frontend Triggers: If the tool result contains data (like weather or stock prices),
            #    you can send a custom event to the UI to display a visual card.
    
    @session.on("close")
    def on_close(event: CloseEvent):
        """
        Triggered when the session ends (User hangs up, Room closes, or Error occurs).
        """
        if event.error:
            logger.error(f"💣 CRASH! Session ended unexpectedly.")
            logger.error(f"   -> Error Details: {event.error}")
            # Useful for: Sending an alert to your Slack/Discord channel for developers.

        # (Normal Hangup)
        else:
            logger.info(f"✅ Normal Closure. User hung up or room ended.")
            # Useful for: Calculating total call duration and billing the client.)

        # Useful for:
        # 1. Cleanup: Close database connections or save final session stats.
        # 2. Analytics: distinct between 'user_hangup' (normal) vs 'error' (crashes).
        # 3. Post-Processing: Trigger a workflow to email a summary of the call to the user.
        # 4. Error Handling: Detect if the session closed due to an unrecoverable error 
        #    (e.g., STT/LLM API failure) and alert the dev team.

            
    # --- START SESSION ---
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=room_io.RoomOptions(),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )

if __name__ == "__main__":
    agents.cli.run_app(server)
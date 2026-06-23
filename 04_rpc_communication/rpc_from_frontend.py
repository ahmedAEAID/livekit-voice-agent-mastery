import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from livekit import agents
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
    """Store user session data with CRUD operations."""

    # Dictionary to store data objects by their ID
    data_objects: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create_object(self, object_type: str, object_data: dict[str, Any]) -> str:
        """Create a new data object with auto-generated ID."""
        object_id = str(uuid.uuid4())

        # Create a container with metadata and the actual data
        data_container = {
            "id": object_id,
            "type": object_type,
            "created_at": datetime.now(UTC).isoformat(),
            "data": object_data,
        }

        # Store in the data dictionary. You could put this in longer term storage
        # if you were building a real production application
        self.data_objects[object_id] = data_container
        return object_id

    def read_object(self, object_id: str) -> dict[str, Any] | None:
        """Read a data object by ID."""
        return self.data_objects.get(object_id)

    def update_object(self, object_id: str, update_data: dict[str, Any]) -> bool:
        """Update a data object by ID."""
        if object_id in self.data_objects:
            # Merge the update data with the existing data
            self.data_objects[object_id]["data"].update(update_data)
            self.data_objects[object_id]["updated_at"] = datetime.now(UTC).isoformat()
            return True
        return False

    def delete_object(self, object_id: str) -> bool:
        """Delete a data object by ID."""
        if object_id in self.data_objects:
            del self.data_objects[object_id]
            return True
        return False

    def list_objects(self, object_type: str | None = None) -> dict[str, dict[str, Any]]:
        """List all objects, optionally filtered by type."""
        if object_type:
            return {k: v for k, v in self.data_objects.items() if v["type"] == object_type}
        return self.data_objects


class RPCStateAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
                You are an agent that manages state through RPC calls
                and also through function calls.

                You can create, read, update, and delete data objects.

                Available functions:
                - create_note: Create a new note
                - update_note: Update an existing note
                - read_note: Read a note by ID
                - list_notes: List all available notes
                - delete_note: Delete a note by ID
            """,
        )

    @function_tool
    async def create_note(self, context: RunContext[UserSessionData], title: str, content: str):
        """Create a new note and store it in the session state.

        Args:
            title: The title of the note
            content: The content of the note
        """
        userdata = context.userdata

        # Create note data
        note_data = {"title": title, "content": content}

        # Store the note in session state
        note_id = userdata.create_object("note", note_data)

        return f"Created note '{title}' with ID: {note_id}"

    @function_tool
    async def read_note(self, context: RunContext[UserSessionData], note_id: str):
        """Read a note by its ID.

        Args:
            note_id: The ID of the note to read
        """
        userdata = context.userdata

        # Read the note from session state
        note = userdata.read_object(note_id)

        if not note:
            return f"Note with ID {note_id} not found."

        note_data = note["data"]
        return f"Note: {note_data['title']}\n\n{note_data['content']}"

    @function_tool
    async def update_note(
        self,
        context: RunContext[UserSessionData],
        note_id: str,
        title: str | None,
        content: str | None,
    ):
        """Update a note by its ID.

        Args:
            note_id: The ID of the note to update
            title: New title for the note (can be null to keep existing)
            content: New content for the note (can be null to keep existing)
        """
        userdata = context.userdata

        # Prepare update data
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content

        if not update_data:
            return "No updates provided."

        # Update the note
        success = userdata.update_object(note_id, update_data)

        if not success:
            return f"Note with ID {note_id} not found."

        return f"Updated note with ID: {note_id}"

    @function_tool
    async def list_notes(self, context: RunContext[UserSessionData]):
        """List all notes currently stored in the session."""
        userdata = context.userdata

        # Get all notes
        notes = userdata.list_objects("note")

        if not notes:
            return "No notes found."

        # Format the response
        response = "Available notes:\n\n"
        for note_id, note in notes.items():
            note_data = note["data"]
            response += f"- {note_data['title']} (ID: {note_id})\n"

        return response

    @function_tool
    async def delete_note(self, context: RunContext[UserSessionData], note_id: str):
        """Delete a note by its ID.

        Args:
            note_id: The ID of the note to delete
        """
        userdata = context.userdata

        # Delete the note
        success = userdata.delete_object(note_id)

        if not success:
            return f"Note with ID {note_id} not found."

        return f"Deleted note with ID: {note_id}"


server = AgentServer()


@server.rtc_session(agent_name="standard_agent")
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()
    userdata = UserSessionData()

    session = create_session(
        user_away_timeout=30.0,
        userdata=userdata,
    )
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant {participant.identity} joined")

    # Initialize UsageCollector
    usage_collector = metrics.UsageCollector()

    async def handle_client_state_operation(rpc_data):
        try:
            if rpc_data.caller_identity != participant.identity:
                logger.warning("Rejected RPC from unexpected participant")
                return json.dumps({"status": "error", "message": "Unauthorized caller"})

            # Extract payload from RpcInvocationData object
            payload_str = rpc_data.payload

            # Parse the JSON payload
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
            if not isinstance(payload, dict):
                return json.dumps({"status": "error", "message": "Payload must be a JSON object"})

            # Extract operation details
            operation = payload.get("operation", "unknown")
            object_type = payload.get("object_type", "unknown")
            object_id = payload.get("object_id")
            object_data = payload.get("data", {})
            if not isinstance(object_data, dict):
                return json.dumps({"status": "error", "message": "data must be a JSON object"})

            result = {"status": "success", "operation": operation, "message": ""}

            # Process the operation
            if operation == "create":
                # Create a new object
                new_id = userdata.create_object(object_type, object_data)
                result["object_id"] = new_id
                result["message"] = f"Created {object_type} with ID: {new_id}"

            elif operation == "read":
                # Read an object
                if not object_id:
                    result["status"] = "error"
                    result["message"] = "Missing object_id for read operation"
                else:
                    obj = userdata.read_object(object_id)
                    if obj:
                        result["object"] = obj
                        result["message"] = f"Retrieved {object_type} with ID: {object_id}"
                    else:
                        result["status"] = "error"
                        result["message"] = f"Object with ID {object_id} not found"

            elif operation == "update":
                # Update an object
                if not object_id:
                    result["status"] = "error"
                    result["message"] = "Missing object_id for update operation"
                else:
                    success = userdata.update_object(object_id, object_data)
                    if success:
                        result["message"] = f"Updated {object_type} with ID: {object_id}"
                    else:
                        result["status"] = "error"
                        result["message"] = f"Object with ID {object_id} not found"

            elif operation == "delete":
                # Delete an object
                if not object_id:
                    result["status"] = "error"
                    result["message"] = "Missing object_id for delete operation"
                else:
                    success = userdata.delete_object(object_id)
                    if success:
                        result["message"] = f"Deleted {object_type} with ID: {object_id}"
                    else:
                        result["status"] = "error"
                        result["message"] = f"Object with ID {object_id} not found"

            elif operation == "list":
                # List objects
                objects = userdata.list_objects(object_type if object_type != "unknown" else None)
                result["objects"] = objects
                result["count"] = len(objects)
                result["message"] = f"Listed {len(objects)} {object_type} objects"

            else:
                result["status"] = "error"
                result["message"] = f"Unknown operation: {operation}"

            return json.dumps(result)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for payload: {e}")
            return json.dumps({"status": "error", "message": f"Invalid JSON: {str(e)}"})
        except Exception:
            logger.exception("Error handling client state operation")
            return json.dumps({"status": "error", "message": "Internal RPC error"})

    # ====== Register RPC method ======
    logger.info("Registering RPC method: agent.state")
    ctx.room.local_participant.register_rpc_method("agent.state", handle_client_state_operation)

    # --- EVENT LISTENERS ---
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
            logger.info(
                f"💰 LLM Cost: {event.metrics.prompt_tokens} prompt + {event.metrics.completion_tokens} completion tokens."
            )

        # B. TTS Latency
        elif isinstance(event.metrics, metrics.TTSMetrics):
            logger.info(f"⚡ TTS Speed: {event.metrics.ttfb}ms to first byte.")

        elif isinstance(event.metrics, metrics.STTMetrics):
            logger.debug("🎤 STT Activity detected.")

    # 3. Log the full session summary when the agent shuts down
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

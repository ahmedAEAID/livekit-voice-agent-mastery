import asyncio
import json

from livekit import api, rtc

from livekit_mastery import get_settings


# --- 1. Token Generation ---
def create_token(identity: str, room_name: str):
    """Generates a JWT Access Token with Video Grants and Agent Dispatch configuration."""
    settings = get_settings()
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_grants(
            api.VideoGrants(
                room=room_name,
                room_join=True,
                can_publish=True,
                can_subscribe=True,
            )
        )
        # Agent Dispatch: Automatically triggers the 'standard_agent' when this participant joins
        .with_room_config(
            api.RoomConfiguration(
                agents=[
                    api.RoomAgentDispatch(
                        agent_name="standard_agent", metadata=json.dumps({"user_id": "12345"})
                    )
                ],
            ),
        )
    )
    return token.to_jwt()


# --- 2. RPC Method Registration ---
def register_rpc_methods(room: rtc.Room):
    """Registers custom RPC methods that the Agent can call remotely."""

    @room.local_participant.register_rpc_method("show_confirmation")
    async def on_confirmation(data: rtc.RpcInvocationData):
        """Handler for the 'show_confirmation' method."""
        print(f"\n🔔 [UI Mock] Received RPC Call from: {data.caller_identity}")
        print(f"💬 Message from Agent: {data.payload}")

        # Simulate a delay (e.g., waiting for a user to click a button)
        print(
            f"⏳ Waiting 5 seconds before returning response (Timeout allowed: {data.response_timeout}s)..."
        )
        await asyncio.sleep(5)

        print("✅ Sending 'yes' response to Agent.")
        return "yes"


# --- 3. Room Connection ---
async def connect_participant(identity: str, room_name: str) -> rtc.Room:
    """Handles the connection process to the LiveKit room."""
    settings = get_settings()
    room = rtc.Room()
    token = create_token(identity, room_name)

    print(f"🔑 Generated a short-lived token for {identity}.")

    @room.on("disconnected")
    def on_disconnected(reason: str):
        print(f"❌ [{identity}] Disconnected from room: {reason}")

    # Connect to the LiveKit server
    await room.connect(settings.livekit_url, token)
    print(f"✅ [{identity}] Connected to room: {room_name}")

    return room


# --- 4. Main Entry Point ---
async def main():
    room_name = "my-room223"
    ui_mock_room = None

    try:
        # Step 1: Connect to the room
        ui_mock_room = await connect_participant("python-ui-mock223", room_name)

        # Step 2: Register RPC methods IMMEDIATELY so they are ready for the Agent
        register_rpc_methods(ui_mock_room)
        print("🚀 RPC Methods are registered and ready for Agent calls.")

        # Step 3: Optional - Wait for the Agent to join
        print("⏳ Waiting for Agent to join the room...")
        agent_joined = False
        for _ in range(10):  # Check for 10 seconds
            if any(
                p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
                for p in ui_mock_room.remote_participants.values()
            ):
                agent_joined = True
                print("🤖 Agent detected in the room!")
                break
            await asyncio.sleep(1)

        if not agent_joined:
            print("⚠️ Warning: Agent has not joined yet, but UI Mock is still listening.")

        print("\nPress Ctrl+C to disconnect and stop the script.")

        # Keep the script running while the room is connected
        while ui_mock_room.isconnected:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping UI Mock (User Interrupted)...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if ui_mock_room and ui_mock_room.isconnected:
            print("🔌 Disconnecting from room...")
            await ui_mock_room.disconnect()
            print("✨ Cleanup complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

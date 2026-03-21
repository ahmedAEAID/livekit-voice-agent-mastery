import os
from livekit.api import (
    AccessToken,
    VideoGrants,
    RoomConfiguration,
    RoomAgentDispatch
)

# Ensure these are set in your environment variables, or pass them directly to AccessToken()
LIVEKIT_URL="wss://hr-meeting-c6qias2x.livekit.cloud"
LIVEKIT_API_KEY="API8JwBWbfBDnSX"
LIVEKIT_API_SECRET="Kezc1wge9880KMeDyJRHXM2xQ48dNB29UzR4DXm3rrHB"
os.environ["LIVEKIT_API_KEY"] = LIVEKIT_API_KEY
os.environ["LIVEKIT_API_SECRET"] = LIVEKIT_API_SECRET

def create_token_with_agent_dispatch(room_name: str) -> str:
    token = (
        AccessToken()
        .with_identity("my-participant2")
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_room_config(
            RoomConfiguration(
                agents=[
                    RoomAgentDispatch(
                        agent_name="Finn-agent", 
                        metadata='{"user_id": "12345"}'
                    )
                ],
            ),
        )
        .to_jwt()
    )
    return token

if __name__ == "__main__":
    jwt = create_token_with_agent_dispatch("my-room")
    print(f"Generated Token:\n{jwt}")
"""Create a participant token that explicitly dispatches a named agent.

Run:
    uv run 03_routing_and_handoffs/token_dispatching.py
"""

from livekit.api import (
    AccessToken,
    RoomAgentDispatch,
    RoomConfiguration,
    VideoGrants,
)

from livekit_mastery import get_settings


def create_token_with_agent_dispatch(
    room_name: str,
    *,
    identity: str = "learning-participant",
    agent_name: str = "standard_agent",
) -> str:
    settings = get_settings()
    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_room_config(
            RoomConfiguration(
                agents=[
                    RoomAgentDispatch(
                        agent_name=agent_name,
                        metadata='{"source": "token-dispatch-lesson"}',
                    )
                ],
            ),
        )
        .to_jwt()
    )
    return token


if __name__ == "__main__":
    jwt = create_token_with_agent_dispatch("my-room")
    print("Token generated successfully.")
    print("For safety, this lesson does not print the JWT. Inspect it only in a secure debugger.")

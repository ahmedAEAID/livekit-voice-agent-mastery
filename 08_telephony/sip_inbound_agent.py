"""Lesson 8: answer inbound phone calls over SIP.

A LiveKit SIP trunk bridges a phone number into a LiveKit room as a normal
participant, so the same agent you already built can answer calls. Two things
change for telephony:

1. Audio is narrowband (8 kHz) and noisy, so use the telephony-tuned noise
   canceller (`BVCTelephony`).
2. The caller only has audio, so keep replies short and confirm details aloud.

This lesson cannot run end-to-end without a configured SIP trunk and dispatch
rule (see README.md), but it compiles and follows the same worker pattern as the
other lessons.

Run (once a trunk routes calls to the `phone_agent`):
    uv run 08_telephony/sip_inbound_agent.py dev
"""

from livekit import agents
from livekit.agents import Agent, AgentServer, room_io
from livekit.plugins import noise_cancellation

from livekit_mastery import create_session


class PhoneAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a friendly phone assistant. The caller hears you over a "
                "phone line, so speak in short, clear sentences and avoid long "
                "lists. When you collect a name, number, or appointment time, "
                "repeat it back to confirm you heard it correctly."
            ),
        )


server = AgentServer()


@server.rtc_session(agent_name="phone_agent")
async def entrypoint(ctx: agents.JobContext) -> None:
    session = create_session()

    await session.start(
        room=ctx.room,
        agent=PhoneAssistant(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # BVCTelephony is tuned for narrowband phone audio; BVC (used by
                # the other lessons) targets wideband microphone input.
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        ),
    )

    await session.generate_reply(
        instructions="Greet the caller warmly and ask how you can help.",
    )


if __name__ == "__main__":
    agents.cli.run_app(server)

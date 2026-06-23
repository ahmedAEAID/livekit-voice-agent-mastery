# Lesson 8: Telephony (inbound SIP)

A LiveKit **SIP trunk** connects a real phone number to LiveKit. When someone
calls, LiveKit places the caller into a room as an ordinary audio participant —
which means the agents you already built can answer the phone with almost no
changes.

[`sip_inbound_agent.py`](sip_inbound_agent.py) shows the two telephony-specific
adjustments:

- **Narrowband noise cancellation** — phone audio is 8 kHz and noisy, so it uses
  `noise_cancellation.BVCTelephony()` instead of the wideband `BVC()` used by the
  microphone lessons.
- **Phone-friendly behavior** — the instructions tell the agent to speak in
  short sentences and confirm details aloud, because the caller has no screen.

## Why it cannot fully run locally

Unlike the other lessons, this one needs LiveKit-side telephony configuration
that lives outside the repository. The Python worker is only half the system.

### Setup outline

1. **Provision a trunk.** Buy a number from a SIP provider (e.g. Twilio,
   Telnyx) and create an **inbound trunk** in LiveKit with the LiveKit CLI:
   `lk sip inbound create`.
2. **Add a dispatch rule.** Tell LiveKit which agent answers. Route inbound
   calls to a room and dispatch the `phone_agent` defined in this lesson:
   `lk sip dispatch-rule create`.
3. **Run the worker.** Start this lesson so it registers the `phone_agent`:
   ```bash
   uv run 08_telephony/sip_inbound_agent.py dev
   ```
4. **Call the number.** The trunk drops the caller into a room, LiveKit
   dispatches your worker, and the agent answers.

See the [LiveKit SIP docs](https://docs.livekit.io/sip/) for the exact trunk and
dispatch-rule fields, plus outbound calling.

## Exercise

Extend the agent with a `transfer_to_human` function tool that uses the LiveKit
SIP API to warm-transfer the caller when the request is out of scope.

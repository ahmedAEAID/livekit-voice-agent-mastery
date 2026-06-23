# Learning Path

Study the lessons in order. Each stage adds one major idea while reusing the
same voice pipeline.

## 1. Basics

### Basic agent

File: `01_basics/basic_agent.py`

Learn:

- how `Agent`, `AgentSession`, and `AgentServer` relate;
- how audio moves through STT, LLM, and TTS;
- how to start a session and generate the first reply.

Exercise: change the persona without changing the shared session factory.

### Prewarming

File: `01_basics/prewarming_agent.py`

Learn why local models such as Silero VAD should be loaded before the first
participant arrives.

Exercise: compare first-response latency with and without the prewarm callback.

### Session configuration

File: `01_basics/session_configuration.py`

Learn interruption thresholds, endpointing, false interruptions, and metrics.

Exercise: test a noisy room with two different `min_interruption_duration`
values and record the behavior.

### Session events

Files:

- `01_basics/session_events.py`
- `01_basics/advanced_session_events.py`

Learn to observe state changes, transcripts, conversation history, tools,
metrics, recoverable errors, and shutdown.

## 2. Tasks and workflows

Study the files in numeric order:

1. consent as a single task;
2. sequential consent and contact collection;
3. unordered structured collection;
4. grouped tasks with regression.

Exercise: add input validation for email addresses and phone numbers without
putting validation logic in the prompt alone.

## 3. Routing and handoffs

`agent_handoffs.py` demonstrates three agents sharing `LeadInfo`:

```text
IntakeAgent → PropertySpecialist → LegalAgent
```

The agents share structured session data and chat context. The handoff is
triggered by tool results rather than a new room.

`token_dispatching.py` demonstrates room-level dispatch before the conversation
starts.

Exercise: add a safe fallback when the budget does not match any property.

## 4. RPC communication

- `rpc_from_frontend.py`: the frontend calls the agent.
- `rpc_to_frontend.py`: the agent calls the frontend.
- `mock_ui_client.py`: a minimal frontend simulator.

Exercise: replace the automatic `"yes"` response with interactive terminal
input and validate the RPC caller identity.

## 5. Custom providers

`livekit_mastery/xtts.py` is the canonical XTTS adapter. The file under
`05_custom_plugins/custom_xtts_plugin/` remains as a small compatibility import
so readers can see how a plugin can be packaged.

Exercise: inject a shared `aiohttp.ClientSession` and measure the latency
difference over repeated requests.

## 6. Testing and evals

`06_testing_and_evals/eval_assistant.py` drives an agent through LiveKit's
text-only test harness (`AgentSession.run(...)`) and asserts on the resulting
events. It shows two patterns: judging a reply against an intent with an LLM
judge, and asserting that the agent called the right function tool.

These evals call a real LLM, so they are excluded from the default `pytest`
run and skip when credentials are missing.

Exercise: add eval cases for error handling, refusals, and misuse resistance.

## 7. Observability and usage metrics

`07_observability/usage_metrics_agent.py` subscribes to the session's
`metrics_collected` event, logs each component's metrics with
`metrics.log_metrics`, and aggregates them with a `UsageCollector`. A shutdown
callback logs one `UsageSummary` for the whole session.

Exercise: convert the summary into a per-call cost using provider pricing.

## 8. Telephony (inbound SIP)

`08_telephony/sip_inbound_agent.py` answers phone calls bridged in through a
LiveKit SIP trunk. It swaps wideband noise cancellation for the telephony-tuned
`BVCTelephony` and adapts the prompt for an audio-only caller. Running it
end-to-end requires a SIP trunk and dispatch rule (see the lesson README).

Exercise: add a `transfer_to_human` tool that warm-transfers the caller.

## 9. Browser web demo

`09_web_demo/server.py` serves a tiny static page (LiveKit JS client over a CDN)
plus a `/token` endpoint that dispatches the named `standard_agent`. It lets you
talk to the agent from a browser and, paired with the lesson 4 RPC agent, shows
the `show_confirmation` dialog rendering for real — the piece the terminal mock
client cannot show.

Exercise: add a transcript panel that displays the conversation as text.

## Suggested capstone

Build a support agent that:

1. collects consent;
2. identifies the request category;
3. hands off to a specialist;
4. asks for UI confirmation before a destructive action;
5. records metrics and a structured final outcome.

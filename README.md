# LiveKit Voice Agent Mastery

A practical learning path for building production-minded voice agents with
LiveKit Agents, OpenAI-compatible LLM/STT APIs, and a custom XTTS server.

The repository is intentionally organized as lessons. Start with the smallest
agent, then move through session behavior, structured workflows, handoffs, RPC,
and custom providers.

## Architecture

```text
Microphone
   │
   ▼
OpenAI-compatible STT
   │ transcript
   ▼
OpenAI-compatible LLM ──► tools, tasks, handoffs, RPC
   │ response text
   ▼
Custom XTTS server
   │ audio
   ▼
LiveKit room
```

All lessons share configuration and provider setup through
[`livekit_mastery/`](livekit_mastery/). This keeps each lesson focused on the
concept it teaches.

## Learning path

| Stage | Topic | Start here |
| --- | --- | --- |
| 1 | Basic agent and prewarming | `01_basics/basic_agent.py` |
| 2 | Session configuration and events | `01_basics/session_configuration.py` |
| 3 | Tasks and structured workflows | `02_tasks_and_workflows/1_simple_task.py` |
| 4 | Routing and agent handoffs | `03_routing_and_handoffs/agent_handoffs.py` |
| 5 | Frontend RPC | `04_rpc_communication/` |
| 6 | Custom TTS provider | `05_custom_plugins/use_custom_tts_agent.py` |

See [the full learning guide](docs/learning_path.md) for objectives, exercises,
and expected behavior.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A LiveKit Cloud project or self-hosted LiveKit server
- An OpenAI-compatible chat-completions API
- An OpenAI-compatible audio-transcriptions API
- An XTTS server exposing `POST /tts_to_audio/`

The XTTS endpoint is expected to accept:

```json
{
  "text": "Hello",
  "language": "en",
  "speaker_wav": "female.wav"
}
```

and return a WAV response.

## Setup

```bash
git clone https://github.com/ahmedAEAID/livekit-voice-agent-mastery.git
cd livekit-voice-agent-mastery
uv sync --locked --dev
cp .env.example .env.local
```

Fill `.env.local` with your own credentials. Never commit this file.

Validate the local project:

```bash
uv run ruff check .
uv run pytest
```

## Run your first lesson

```bash
uv run 01_basics/basic_agent.py dev
```

Useful alternatives:

```bash
uv run 05_custom_plugins/use_custom_tts_agent.py console
uv run 01_basics/prewarming_agent.py download-files
uv run 01_basics/prewarming_agent.py dev
```

## Running the RPC example

Use two terminals:

```bash
# Terminal 1
uv run 04_rpc_communication/rpc_to_frontend.py dev

# Terminal 2
uv run 04_rpc_communication/mock_ui_client.py
```

The mock UI registers `show_confirmation`; the agent calls it when a visible
confirmation is required.

## Shared modules

- `livekit_mastery/config.py`: validates `.env.local`.
- `livekit_mastery/session.py`: creates the shared STT → LLM → XTTS pipeline.
- `livekit_mastery/xtts.py`: adapts the XTTS HTTP endpoint to LiveKit TTS.

## Security

- Keep credentials only in `.env.local` or a secret manager.
- Never print participant JWTs.
- Generate tokens server-side and keep them short-lived.
- Rotate any credential that has appeared in source code, logs, screenshots,
  chat messages, or Git history.

See [Security](docs/security.md) before deploying publicly.

## Troubleshooting

Read [Troubleshooting](docs/troubleshooting.md) for configuration errors,
provider compatibility, XTTS failures, dispatch mismatches, and model downloads.

## Project quality

The repository includes:

- Ruff linting and formatting
- Pytest tests
- Python compilation checks
- GitHub Actions quality checks
- Gitleaks secret scanning

This is a learning repository, not a drop-in production service. Production
deployments still need authentication, persistence, rate limiting, monitoring,
and provider-specific reliability work.

# Troubleshooting

## Missing required configuration

Copy `.env.example` to `.env.local` and fill every value. The shared config
module reports the exact missing environment variable.

## The worker starts but no agent joins

Check that the dispatched `agent_name` exactly matches the name declared by
`@server.rtc_session(...)` or `WorkerOptions`.

## LLM works but STT fails

An API can be OpenAI-compatible for chat without supporting
`/audio/transcriptions`. Verify the provider supports the selected STT model and
endpoint.

## XTTS returns no audio

Verify:

- `XTTS_BASE_URL` is reachable from the agent host;
- `POST /tts_to_audio/` exists;
- `VOICE_WAV_NAME` exists on the XTTS server;
- the endpoint returns WAV audio;
- the returned audio matches the configured sample rate.

Test the service independently before starting LiveKit.

## The voice language is wrong

Set `XTTS_LANGUAGE` to the language expected by your XTTS server. Arabic lessons
can override the session language with `create_session(language="ar")`.

## Model files are missing

Run:

```bash
uv run 01_basics/prewarming_agent.py download-files
```

## `uv sync --locked` fails

The lockfile and `pyproject.toml` are out of sync. Maintainers should run
`uv lock`, review the dependency diff, and commit both files together.

## RPC times out

Make sure the frontend participant:

- joined the same room;
- registered the exact RPC method name;
- remained connected;
- responded before `response_timeout`.

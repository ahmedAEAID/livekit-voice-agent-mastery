# Lesson 6: Testing and evals

Voice agents are non-deterministic, so "did it behave correctly?" is hard to
answer with a unit test. LiveKit Agents ships a text-only test harness that runs
your agent through `AgentSession.run(...)` and lets you assert on the events it
produces — including an **LLM-as-judge** for intent-level checks.

## What this lesson shows

[`eval_assistant.py`](eval_assistant.py) demonstrates two patterns:

- **Behavioral eval** — run the agent on an input, then `judge` the reply against
  a stated intent ("a brief, friendly greeting").
- **Tool-use assertion** — confirm the agent chose to call `get_weather` instead
  of hallucinating an answer.

## Running

These evals call a real LLM, so they are **excluded from the default test run**
(`testpaths` in `pyproject.toml` points only at `tests/`). Run them explicitly:

```bash
uv run pytest 06_testing_and_evals/eval_assistant.py -v
```

They use the same LLM credentials as the rest of the course (from `.env.local`).
If those are missing, each test **skips** rather than failing — so the lesson is
safe to clone and inspect without keys.

## Why this matters

This is the difference between "it worked when I tried it" and a regression
suite you can run on every change. Extend it with cases for error handling,
refusals, grounding, and misuse resistance as your agent grows.

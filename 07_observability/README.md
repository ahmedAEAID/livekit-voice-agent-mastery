# Lesson 7: Observability and usage metrics

You cannot improve what you cannot measure. Every component in the pipeline
emits structured metrics, and LiveKit gives you two helpers to use them:

- `metrics.log_metrics(ev.metrics)` — pretty-prints each component's metrics
  (STT, LLM, TTS, VAD, end-of-utterance latency) as they arrive.
- `UsageCollector` — aggregates those metrics across the whole conversation and
  produces a single `UsageSummary` (tokens, audio duration) you can log or bill.

## What this lesson shows

[`usage_metrics_agent.py`](usage_metrics_agent.py):

1. Subscribes to the session's `metrics_collected` event.
2. Logs each metric and feeds it into a `UsageCollector`.
3. Registers a **shutdown callback** so the usage summary is logged once, after
   the call ends and reflects the entire session.

## Running

```bash
uv run 07_observability/usage_metrics_agent.py dev
```

Talk to the agent, then end the session — the worker logs per-turn metrics live
and a final `Session usage summary: ...` line on shutdown.

## Going further

- Export metrics to Prometheus by scraping the worker's `/metrics` endpoint.
- Send traces to an OpenTelemetry collector for end-to-end latency breakdowns.
- Turn the summary into a cost figure using your provider's per-token pricing.

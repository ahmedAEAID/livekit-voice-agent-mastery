# Lesson 9: Browser web demo

Most lessons can be tried from the terminal with `console` mode. This one adds a
tiny browser frontend so you can:

- talk to the agent from a web page, and
- **see the RPC confirmation dialog render for real** — the part the terminal
  mock client (`04_rpc_communication/mock_ui_client.py`) cannot show.

It is deliberately minimal: one static page that loads the LiveKit JS client
from a CDN, plus a small Python server that mints a token and serves the files.

## Files

| File | Role |
| --- | --- |
| `server.py` | aiohttp server: `/token` mints a token that dispatches `standard_agent`, `/` serves the page |
| `static/index.html` | Connect button, status line, and the confirmation modal |
| `static/app.js` | Connects, publishes the mic, plays agent audio, registers the `show_confirmation` RPC method |
| `static/styles.css` | Small dark theme |

## Run

You need two terminals: one for the agent, one for this server.

```bash
# Terminal 1 — an agent that registers the named "standard_agent"
uv run 04_rpc_communication/rpc_to_frontend.py dev    # agent -> frontend RPC
# or
uv run 04_rpc_communication/rpc_from_frontend.py dev  # frontend -> agent RPC

# Terminal 2 — the web demo
uv run 09_web_demo/server.py
```

> **Open <http://localhost:8080>, not `0.0.0.0:8080`.** Browsers only expose the
> microphone on a secure context (https or `localhost`), so `0.0.0.0` silently
> blocks the mic and the agent never hears you. The page warns you if this
> happens.

Click **Connect & talk** and allow microphone access. The activity log shows
each step (connect, agent joining, audio, RPC).

### RPC in both directions

- **Agent → frontend:** run `rpc_to_frontend.py`. When the agent needs a
  decision it calls `show_confirmation` and a **Yes/No** dialog appears; your
  answer is returned to the agent.
- **Frontend → agent:** run `rpc_from_frontend.py`. Use the **Create note**
  panel to send an `agent.state` RPC; the agent stores the note and replies with
  a status message shown in the log.

> Any lesson that uses `agent_name="standard_agent"` works here — the token
> dispatches that agent into the room.

## How it connects

```text
Browser ──GET /token──► server.py ──mints JWT (dispatch standard_agent)──► Browser
Browser ──room.connect(url, token)──► LiveKit room ◄── agent dispatched by token
Agent ──perform_rpc("show_confirmation", payload)──► Browser modal ──"yes"/"no"──► Agent
```

## Notes

- The token is short-lived (15 minutes) and minted server-side; the API secret
  never reaches the browser.
- This is a demo client, not a production frontend. A real app would add
  reconnection handling, auth, and a proper build setup.

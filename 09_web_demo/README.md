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
# Terminal 1 — the RPC agent (registers the named "standard_agent")
uv run 04_rpc_communication/rpc_to_frontend.py dev

# Terminal 2 — the web demo
uv run 09_web_demo/server.py
```

Open <http://localhost:8080>, click **Connect & talk**, and allow microphone
access. The agent greets you; when it needs a decision it calls
`show_confirmation`, and the **Yes/No** dialog appears in the page. Your choice
is returned to the agent over RPC.

> Any other lesson that uses `agent_name="standard_agent"` works here too — the
> token dispatches that agent into the room.

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

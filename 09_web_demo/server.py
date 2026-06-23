"""Lesson 9: a minimal browser frontend for the voice agent.

Most lessons can be tried from the terminal with `console` mode. This lesson is
different: it serves a tiny web page so you can talk to the agent from a browser
*and see the RPC confirmation UI render for real* — the piece the terminal mock
client cannot show.

It is intentionally dependency-free on the frontend: a single static page loads
the LiveKit JS client from a CDN. This Python server only does two jobs:

1. Mint a short-lived access token that dispatches the named `standard_agent`.
2. Serve the static files.

Run:
    uv run 09_web_demo/server.py
    # then open http://localhost:8080

Pair it with the RPC agent in another terminal so the confirmation modal fires:
    uv run 04_rpc_communication/rpc_to_frontend.py dev
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from pathlib import Path

from aiohttp import web
from livekit import api

from livekit_mastery import get_settings

logger = logging.getLogger("web-demo")

STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST = "0.0.0.0"
PORT = 8080
TOKEN_TTL = timedelta(minutes=15)
AGENT_NAME = "standard_agent"


def _mint_token(identity: str, room_name: str) -> str:
    """Create a participant token that also dispatches the named agent."""

    settings = get_settings()
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_ttl(TOKEN_TTL)
        .with_grants(
            api.VideoGrants(
                room=room_name,
                room_join=True,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .with_room_config(
            api.RoomConfiguration(
                agents=[api.RoomAgentDispatch(agent_name=AGENT_NAME)],
            )
        )
    )
    return token.to_jwt()


async def handle_token(request: web.Request) -> web.Response:
    """Return a fresh token plus the LiveKit URL for the browser to connect."""

    settings = get_settings()
    room_name = request.query.get("room") or "web-demo"
    identity = request.query.get("identity") or f"web-user-{uuid.uuid4().hex[:8]}"

    body = {
        "url": settings.livekit_url,
        "token": _mint_token(identity, room_name),
        "room": room_name,
        "identity": identity,
    }
    logger.info("Issued token for %s in room %s", identity, room_name)
    return web.json_response(body)


async def handle_index(_: web.Request) -> web.Response:
    return web.FileResponse(STATIC_DIR / "index.html")


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/token", handle_token)
    app.router.add_static("/static/", STATIC_DIR, name="static")
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Fail fast with a clear message if .env.local is missing values.
    get_settings()
    logger.info("Open http://localhost:%s", PORT)
    web.run_app(build_app(), host=HOST, port=PORT)

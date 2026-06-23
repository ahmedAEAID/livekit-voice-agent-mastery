from pathlib import Path


def test_dispatch_lesson_contains_no_hardcoded_livekit_secret() -> None:
    source = Path("03_routing_and_handoffs/token_dispatching.py").read_text()

    assert "LIVEKIT_API_SECRET=" not in source
    assert "Generated Token:\\n" not in source


def test_local_environment_is_gitignored() -> None:
    patterns = Path(".gitignore").read_text().splitlines()

    assert ".env.local" in patterns

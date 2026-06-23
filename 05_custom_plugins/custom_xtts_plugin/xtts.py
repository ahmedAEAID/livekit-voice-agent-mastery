"""Compatibility import for the custom-plugin lesson.

The production implementation lives in ``livekit_mastery.xtts`` so every
lesson uses the same tested adapter.
"""

from livekit_mastery.xtts import CustomXTTS, XTTSChunkedStream

__all__ = ["CustomXTTS", "XTTSChunkedStream"]

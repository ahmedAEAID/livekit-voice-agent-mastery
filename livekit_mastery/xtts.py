"""A defensive LiveKit TTS adapter for a streaming XTTS server.

It targets the XTTS `/tts_stream` endpoint, which begins returning audio while
the model is still synthesizing. Streaming the audio out chunk by chunk lowers
the time-to-first-byte compared with waiting for a full `/tts_to_audio/` file.

The endpoint returns a streaming WAV (`audio/x-wav`): a 44-byte RIFF/PCM header
with placeholder sizes, followed by signed 16-bit little-endian PCM at 24 kHz
mono. We strip that header and push the raw PCM, because a WAV whose declared
data size is zero can stop a strict decoder early.
"""

from __future__ import annotations

import uuid

import aiohttp
from livekit.agents import APIConnectionError, APIStatusError, APITimeoutError, tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

# Standard RIFF/PCM WAV header length emitted by the XTTS streaming endpoint.
WAV_HEADER_BYTES = 44
# How many bytes to read from the socket per push to the audio emitter.
STREAM_READ_SIZE = 4096
DEFAULT_STREAM_CHUNK_SIZE = 150


class XTTSChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts_service: CustomXTTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(tts=tts_service, input_text=input_text, conn_options=conn_options)
        self._xtts = tts_service

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        params = {
            "text": self.input_text,
            "language": self._xtts.language,
            "speaker_wav": self._xtts.speaker_wav,
            "stream_chunk_size": str(self._xtts.stream_chunk_size),
        }
        timeout = aiohttp.ClientTimeout(total=self._conn_options.timeout)
        header_remaining = WAV_HEADER_BYTES
        received_audio = False

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self._xtts.endpoint, params=params) as response:
                    if response.status != 200:
                        detail = (await response.text())[:500]
                        raise APIStatusError(
                            f"XTTS returned HTTP {response.status}: {detail}",
                            status_code=response.status,
                            request_id=response.headers.get("x-request-id"),
                            body=detail,
                        )

                    output_emitter.initialize(
                        request_id=str(uuid.uuid4()),
                        sample_rate=self._xtts.sample_rate,
                        num_channels=self._xtts.num_channels,
                        mime_type="audio/pcm",
                    )

                    async for chunk in response.content.iter_chunked(STREAM_READ_SIZE):
                        if not chunk:
                            continue
                        # Drop the leading WAV header, possibly split across reads.
                        if header_remaining:
                            drop = min(header_remaining, len(chunk))
                            header_remaining -= drop
                            chunk = chunk[drop:]
                            if not chunk:
                                continue
                        output_emitter.push(chunk)
                        received_audio = True
        except TimeoutError as exc:
            raise APITimeoutError("XTTS request timed out") from exc
        except aiohttp.ClientError as exc:
            raise APIConnectionError(f"Could not connect to XTTS: {exc}") from exc

        if not received_audio:
            raise APIConnectionError("XTTS returned an empty audio response")

        output_emitter.flush()


class CustomXTTS(tts.TTS):
    """Wrap an XTTS `/tts_stream` HTTP endpoint as a LiveKit TTS provider."""

    def __init__(
        self,
        server_url: str,
        speaker_wav: str,
        language: str = "en",
        sample_rate: int = 24000,
        stream_chunk_size: int = DEFAULT_STREAM_CHUNK_SIZE,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self.server_url = server_url.rstrip("/")
        self.speaker_wav = speaker_wav
        self.language = language
        self.stream_chunk_size = stream_chunk_size

    @property
    def endpoint(self) -> str:
        return f"{self.server_url}/tts_stream"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        **kwargs: object,
    ) -> tts.ChunkedStream:
        return XTTSChunkedStream(
            tts_service=self,
            input_text=text,
            conn_options=conn_options,
        )

"""A defensive LiveKit TTS adapter for an OpenAI-independent XTTS server."""

from __future__ import annotations

import uuid

import aiohttp
from livekit.agents import APIConnectionError, APIStatusError, APITimeoutError, tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions


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
        payload = {
            "text": self.input_text,
            "language": self._xtts.language,
            "speaker_wav": self._xtts.speaker_wav,
        }
        timeout = aiohttp.ClientTimeout(total=self._conn_options.timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self._xtts.endpoint, json=payload) as response:
                    if response.status != 200:
                        detail = (await response.text())[:500]
                        raise APIStatusError(
                            f"XTTS returned HTTP {response.status}: {detail}",
                            status_code=response.status,
                            request_id=response.headers.get("x-request-id"),
                            body=detail,
                        )
                    audio_bytes = await response.read()
        except TimeoutError as exc:
            raise APITimeoutError("XTTS request timed out") from exc
        except aiohttp.ClientError as exc:
            raise APIConnectionError(f"Could not connect to XTTS: {exc}") from exc

        if not audio_bytes:
            raise APIConnectionError("XTTS returned an empty audio response")

        output_emitter.initialize(
            request_id=str(uuid.uuid4()),
            sample_rate=self._xtts.sample_rate,
            num_channels=self._xtts.num_channels,
            mime_type="audio/wav",
        )
        output_emitter.push(audio_bytes)
        output_emitter.flush()


class CustomXTTS(tts.TTS):
    """Wrap an XTTS `/tts_to_audio/` HTTP endpoint as a LiveKit TTS provider."""

    def __init__(
        self,
        server_url: str,
        speaker_wav: str,
        language: str = "en",
        sample_rate: int = 24000,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self.server_url = server_url.rstrip("/")
        self.speaker_wav = speaker_wav
        self.language = language

    @property
    def endpoint(self) -> str:
        return f"{self.server_url}/tts_to_audio/"

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

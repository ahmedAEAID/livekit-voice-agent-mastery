import aiohttp
from livekit.agents import tts
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS

class XTTSChunkedStream(tts.ChunkedStream):
    def __init__(self, *, tts_service: "CustomXTTS", input_text: str, conn_options: APIConnectOptions) -> None:
        super().__init__(tts=tts_service, input_text=input_text, conn_options=conn_options)
        self._xtts = tts_service

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": self.input_text,
                    "language": self._xtts.language,
                    "speaker_wav": self._xtts.speaker_wav
                }
                
                url = f"{self._xtts.server_url}/tts_to_audio/"
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        audio_bytes = await response.read()
                        
                        output_emitter.initialize(
                            request_id="",
                            sample_rate=24000, 
                            num_channels=1,
                            mime_type="audio/wav" 
                        )
                        
                        output_emitter.push(audio_bytes)
                        output_emitter.flush()
                    else:
                        error_text = await response.text()
                        print(f"XTTS Server Error: {response.status} - {error_text}")
        except Exception as e:
            print(f"Error connecting to XTTS: {e}")


class CustomXTTS(tts.TTS):
    def __init__(self, server_url: str, speaker_wav: str, language: str = "ar"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1
        )
        self.server_url = server_url
        self.speaker_wav = speaker_wav
        self.language = language

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS, **kwargs
    ) -> tts.ChunkedStream:
        return XTTSChunkedStream(tts_service=self, input_text=text, conn_options=conn_options)
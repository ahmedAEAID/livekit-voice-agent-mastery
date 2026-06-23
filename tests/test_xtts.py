from livekit_mastery.xtts import CustomXTTS


def test_xtts_endpoint_normalizes_trailing_slash() -> None:
    provider = CustomXTTS(
        server_url="http://localhost:8044/",
        speaker_wav="female.wav",
    )

    assert provider.endpoint == "http://localhost:8044/tts_stream"
    assert provider.language == "en"
    assert provider.stream_chunk_size == 150

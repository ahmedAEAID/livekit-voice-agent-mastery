from livekit_mastery.xtts import CustomXTTS


def test_xtts_endpoint_normalizes_trailing_slash() -> None:
    provider = CustomXTTS(
        server_url="http://localhost:8044/",
        speaker_wav="female.wav",
    )

    assert provider.endpoint == "http://localhost:8044/tts_to_audio/"
    assert provider.language == "en"

import io
import wave
import aiohttp

from livekit.agents import stt
from livekit.agents.types import (
    APIConnectOptions,
    DEFAULT_API_CONNECT_OPTIONS,
)
from livekit import rtc


class ParakeetWavSTT(stt.STT):
    def __init__(
        self,
        base_url="http://127.0.0.1:8090/v1",
        model="parakeet",
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False,
                offline_recognize=True,
            )
        )

        self.base_url = base_url.rstrip("/")
        self._parakeet_model = model

    async def _recognize_impl(
        self,
        buffer,
        *,
        language=None,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
    ):
        wav_bytes = self._make_wav(buffer)

        form = aiohttp.FormData()
        form.add_field(
            "file",
            wav_bytes,
            filename="audio.wav",
            content_type="audio/wav",
        )
        form.add_field(
            "model",
            self._parakeet_model,
        )
        form.add_field(
            "response_format",
            "json",
        )

        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.base_url}/audio/transcriptions",
                data=form,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        text = data.get("text", "").strip()

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(
                    language="en",
                    text=text,
                )
            ],
        )

    def _make_wav(self, buffer) -> bytes:
        output = io.BytesIO()

        with wave.open(output, "wb") as wav:
            wav.setnchannels(buffer.num_channels)
            wav.setsampwidth(2)
            wav.setframerate(buffer.sample_rate)
            wav.writeframes(buffer.data.tobytes())

        return output.getvalue()

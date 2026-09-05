import uuid

import aiohttp
from livekit.agents import tts
from livekit.agents.types import (
    APIConnectOptions,
    DEFAULT_API_CONNECT_OPTIONS,
)


class KokoroTTS(tts.TTS):
    def __init__(
        self,
        *,
        base_url="http://127.0.0.1:8880/v1",
        voice="af_jessica",
        model="kokoro",
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,
                aligned_transcript=False,
            ),
            sample_rate=24000,
            num_channels=1,
        )

        self.base_url = base_url.rstrip("/")
        self.voice = voice
        self._kokoro_model = model

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ):
        return KokoroStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )


class KokoroStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts,
        input_text,
        conn_options,
    ):
        super().__init__(
            tts=tts,
            input_text=input_text,
            conn_options=conn_options,
        )

        self._kokoro = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        request_id = str(uuid.uuid4())

        output_emitter.initialize(
            request_id=request_id,
            sample_rate=24000,
            num_channels=1,
            mime_type="audio/pcm",
        )

        payload = {
            "model": self._kokoro._kokoro_model,
            "input": self._input_text,
            "voice": self._kokoro.voice,
            "response_format": "pcm",
        }

        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self._kokoro.base_url}/audio/speech",
                json=payload,
            ) as response:

                response.raise_for_status()

                async for chunk in response.content.iter_chunked(4096):
                    if chunk:
                        output_emitter.push(chunk)

        output_emitter.flush()

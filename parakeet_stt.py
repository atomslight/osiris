import asyncio
import ctypes
import os
import uuid
from pathlib import Path

import numpy as np
from livekit.agents import stt
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit import rtc


BASE_DIR = Path(__file__).resolve().parent
NATIVE_DIR = BASE_DIR / "parakeet" / "parakeet.cpp" / "native"
MODEL_PATH = BASE_DIR / "parakeet" / "parakeet.cpp" / "models" / "realtime_eou_120m-v1-q8_0.gguf"

# Make Windows find CUDA + GGML DLL dependencies.
_dll_dir = os.add_dll_directory(str(NATIVE_DIR))
_lib = ctypes.CDLL(str(NATIVE_DIR / "parakeet.dll"))


# ---- C API signatures ----

_lib.parakeet_capi_load.argtypes = [ctypes.c_char_p]
_lib.parakeet_capi_load.restype = ctypes.c_void_p

_lib.parakeet_capi_free.argtypes = [ctypes.c_void_p]
_lib.parakeet_capi_free.restype = None

_lib.parakeet_capi_last_error.argtypes = [ctypes.c_void_p]
_lib.parakeet_capi_last_error.restype = ctypes.c_char_p

_lib.parakeet_capi_stream_begin.argtypes = [ctypes.c_void_p]
_lib.parakeet_capi_stream_begin.restype = ctypes.c_void_p

_lib.parakeet_capi_stream_feed.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int),
]
_lib.parakeet_capi_stream_feed.restype = ctypes.c_void_p

_lib.parakeet_capi_stream_finalize.argtypes = [ctypes.c_void_p]
_lib.parakeet_capi_stream_finalize.restype = ctypes.c_void_p

_lib.parakeet_capi_stream_free.argtypes = [ctypes.c_void_p]
_lib.parakeet_capi_stream_free.restype = None

_lib.parakeet_capi_free_string.argtypes = [ctypes.c_void_p]
_lib.parakeet_capi_free_string.restype = None


PARAKEET_EVENT_EOU = 1
PARAKEET_EVENT_EOB = 2


def _read_c_string(ptr) -> str:
    if not ptr:
        return ""

    try:
        return ctypes.string_at(ptr).decode("utf-8")
    finally:
        _lib.parakeet_capi_free_string(ptr)


def _frame_to_float32(frame: rtc.AudioFrame) -> np.ndarray:
    samples = np.frombuffer(frame.data, dtype=np.int16)

    if frame.num_channels > 1:
        samples = samples.reshape(-1, frame.num_channels).mean(axis=1)

    return samples.astype(np.float32) / 32768.0


class ParakeetStream(stt.RecognizeStream):
    def __init__(
        self,
        *,
        stt_instance: "ParakeetSTT",
        conn_options: APIConnectOptions,
    ):
        super().__init__(
            stt=stt_instance,
            conn_options=conn_options,
            sample_rate=16000,
        )

        self._stt_instance = stt_instance
        self._stream = None
        self._started = False
        self._utterance = ""

    async def _run(self) -> None:
        ctx = self._stt_instance._ctx

        self._stream = _lib.parakeet_capi_stream_begin(ctx)

        if not self._stream:
            error = _lib.parakeet_capi_last_error(ctx)
            message = error.decode("utf-8") if error else "failed to start Parakeet stream"
            raise RuntimeError(message)

        try:
            async for item in self._input_ch:
                if isinstance(item, self._FlushSentinel):
                    continue

                frame = item
                pcm = _frame_to_float32(frame)

                if pcm.size == 0:
                    continue

                text, events = await asyncio.to_thread(
                    self._feed,
                    pcm,
                )

                if text:
                    self._utterance = (
                        f"{self._utterance} {text}".strip()
                    )

                    if not self._started:
                        self._started = True
                        self._event_ch.send_nowait(
                            stt.SpeechEvent(
                                type=stt.SpeechEventType.START_OF_SPEECH,
                                request_id=self._stt_instance.request_id,
                            )
                        )

                    self._event_ch.send_nowait(
                        stt.SpeechEvent(
                            type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                            request_id=self._stt_instance.request_id,
                            alternatives=[
                                stt.SpeechData(
                                    language="en",
                                    text=self._utterance,
                                )
                            ],
                        )
                    )

                # EOU = user completed a turn.
                if events & PARAKEET_EVENT_EOU:
                    if self._utterance:
                        self._event_ch.send_nowait(
                            stt.SpeechEvent(
                                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                                request_id=self._stt_instance.request_id,
                                alternatives=[
                                    stt.SpeechData(
                                        language="en",
                                        text=self._utterance,
                                    )
                                ],
                            )
                        )

                    self._event_ch.send_nowait(
                        stt.SpeechEvent(
                            type=stt.SpeechEventType.END_OF_SPEECH,
                            request_id=self._stt_instance.request_id,
                        )
                    )

                    self._utterance = ""
                    self._started = False

            # Flush remaining audio when the stream ends.
            final_text = await asyncio.to_thread(self._finalize)

            if final_text:
                self._utterance = f"{self._utterance} {final_text}".strip()

                if self._utterance:
                    self._event_ch.send_nowait(
                        stt.SpeechEvent(
                            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                            request_id=self._stt_instance.request_id,
                            alternatives=[
                                stt.SpeechData(
                                    language="en",
                                    text=self._utterance,
                                )
                            ],
                        )
                    )

        finally:
            if self._stream:
                _lib.parakeet_capi_stream_free(self._stream)
                self._stream = None

    def _feed(self, pcm: np.ndarray):
        eou = ctypes.c_int(0)

        ptr = pcm.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

        result = _lib.parakeet_capi_stream_feed(
            self._stream,
            ptr,
            pcm.size,
            ctypes.byref(eou),
        )

        text = _read_c_string(result)

        return text.strip(), eou.value

    def _finalize(self):
        result = _lib.parakeet_capi_stream_finalize(self._stream)
        return _read_c_string(result).strip()


class ParakeetSTT(stt.STT):
    def __init__(self):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
                offline_recognize=False,
            )
        )

        self.request_id = uuid.uuid4().hex

        self._ctx = _lib.parakeet_capi_load(
            str(MODEL_PATH).encode("utf-8")
        )

        if not self._ctx:
            raise RuntimeError(
                f"Failed to load Parakeet model: {MODEL_PATH}"
            )

    def stream(
        self,
        *,
        language=None,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
    ):
        return ParakeetStream(
            stt_instance=self,
            conn_options=conn_options,
        )

    async def _recognize_impl(
        self,
        buffer,
        *,
        language=None,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
    ):
        raise NotImplementedError(
            "ParakeetSTT is configured for native streaming only."
        )

    async def aclose(self):
        if self._ctx:
            _lib.parakeet_capi_free(self._ctx)
            self._ctx = None

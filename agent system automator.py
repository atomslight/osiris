import asyncio
import logging
import os
from datetime import datetime
from livekit.plugins import ai_coustics,silero
from livekit.agents.metrics import STTMetrics




from dotenv import load_dotenv
from kokoro_tts import KokoroTTS
from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    TurnHandlingOptions,
    function_tool,
    get_job_context,
    inference,
    room_io,
    llm,
    stt,
    tts
)
import httpx
from openai import AsyncOpenAI
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.agents import APIConnectOptions

import asyncio
from shutdown import shutdown_pc
from parakeet_wav_stt import ParakeetWavSTT
from parakeet_stt import ParakeetSTT
from livekit.plugins import noise_cancellation, google, openai, assemblyai, deepgram

load_dotenv()
import io
import wave
import aiohttp

from livekit.agents import stt
from livekit.agents.types import (
    APIConnectOptions,
    DEFAULT_API_CONNECT_OPTIONS,
)
from livekit import rtc

ollama_client_31b = AsyncOpenAI(
    base_url="http://127.0.0.1:11434/v1",
    api_key="ollama",
    timeout=httpx.Timeout(
        connect=30.0,
        read=120.0,
        write=30.0,
        pool=30.0,
    ),
)

ollama_client_8b = AsyncOpenAI(
    base_url="http://127.0.0.1:11434/v1",
    api_key="ollama",
    timeout=httpx.Timeout(
        connect=30.0,
        read=60.0,
        write=30.0,
        pool=30.0,
    ),
)


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


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=
                                """You are **OSIRIS**, an AI system monitor and automation assistant.

                                Activate only when the user explicitly addresses you with **"OSIRIS"**.

                                Examples:
                                - **"OSIRIS, shut down the PC"** → Execute the shutdown action.
                                - **"Shut down the PC"** → Do not activate or execute.
                                - **"OSIRIS, check Docker"** → Check Docker status.
                                - **"Check Docker"** → Do not activate or execute.

                                Responsibilities:
                                - Monitor CPU, RAM, GPU, VRAM, disk, processes, services, Docker, and system health.
                                - Execute approved system and automation tasks.
                                - Detect and diagnose failures using available system information and logs.
                                - Automate repetitive workflows.
                                - Report actions and results concisely.
                                - Never claim success without tool confirmation.

                                **Exit:** Use `exit_app` only for explicit OSIRIS-directed requests to quit, exit, stop, end, or close the app.

                                **Shutdown:** Use `shutdown_pc` only for an explicit OSIRIS-directed shutdown request.
                                # Listening controls

                                - If the user says:
                                  "OSIRIS stop listening"
                                  "OSIRIS pause listening"
                                  "OSIRIS mute yourself"
                                  "OSIRIS don't listen" ..etc similar
                                  
                                  then call the `pause_listening` tool.

                                - If the user says:
                                  "OSIRIS resume listening"
                                  "OSIRIS start listening"
                                  "OSIRIS wake up" ..etc similar
                                  
                                  then call the `resume_listening` tool.

                                - Never pause or resume listening unless the user explicitly addresses OSIRIS.
                                Greetings such as "Good night", "Bye", or "See you" do not trigger OSIRIS or shutdown.
                """,tools=[shutdown_pc],
            )

    @function_tool()
    async def exit_app(self, context: RunContext) -> str:
        """
        Close the assistant when the user wants to exit,
        quit, stop, or end the conversation.
        """
        context.disallow_interruptions()
        await self.session.say("Goodbye. Closing the assistant.")
        print("Shutting down LiveKit agent...")
        job_ctx = get_job_context()
        job_ctx.shutdown(reason="user requested exit")
        await asyncio.sleep(2)  # let the goodbye audio finish playing
        os._exit(0)
        return "Assistant closed."
    @function_tool()
    async def pause_listening(self, context: RunContext) -> str:
        """
        Pause microphone listening temporarily.
        """
        self.session.interrupt()
        self.session.input.set_audio_enabled(False)

        await self.session.say("Listening paused.")
        return "Listening paused."


    @function_tool()
    async def resume_listening(self, context: RunContext) -> str:
        """
        Resume microphone listening.
        """
        self.session.input.set_audio_enabled(True)

        await self.session.say("Listening resumed.")
        return "Listening resumed."

server = AgentServer()


def get_greeting() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 18:
        return "Good Afternoon"
    else:
        return "Good Evening"


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    aic_vad = ai_coustics.VAD()

    session = AgentSession(
        stt=stt.FallbackAdapter([
            inference.STT(
                model="deepgram/nova-3",
                language="en-US",
            ),
            stt.StreamAdapter(
                stt=ParakeetWavSTT(
                    base_url="http://127.0.0.1:8090/v1",
                ),
                vad=aic_vad,
            ),
        ]),

        llm=llm.FallbackAdapter(
            [
                inference.LLM(
                    model="gpt-5.4-nano",
                ),
                google.LLM(
                                model="gemini-3-flash-preview",
                            ),
                            openai.LLM(
                                                            model="gemma4:31b-cloud",
                                                            #base_url="http://localhost:11434/v1",
                                                            client=ollama_client_31b,
                                            
                                                        ),
                            openai.LLM(
                                model="llama3.1:8b",
                                #base_url="http://localhost:11434/v1",
                                client=ollama_client_8b,
                
                            ),
                            
            ],
            attempt_timeout=30.0,
            max_retry_per_llm=0,
            retry_interval=1.0,
        ),
            
            
        tts=tts.FallbackAdapter([
            inference.TTS(
                model="deepgram/aura-2",
                voice="athena",
                language="en",
            ),
            KokoroTTS(
                base_url="http://127.0.0.1:8880/v1",
                voice="af_jessica",
            ),
        ]),

        conn_options=SessionConnectOptions(
            llm_conn_options=APIConnectOptions(
                max_retry=2,
                retry_interval=2.0,
                timeout=360.0,
            ),
            stt_conn_options=APIConnectOptions(
                max_retry=1,
                retry_interval=1.0,
                timeout=30.0,
            ),
            tts_conn_options=APIConnectOptions(
                max_retry=1,
                retry_interval=1.0,
                timeout=30.0,
            ),
        ),

        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(
                unlikely_threshold=0.5,
            ),
            endpointing={
                "mode": "fixed",
                "min_delay": 0.8,
                "max_delay": 1.8,
            },
            interruption={
                "mode": "vad",
                "min_duration": 0.1,
                "resume_false_interruption": False,
            },
        ),
    )

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                )
            ),
        ),
    )

    greeting = get_greeting()
    await session.say(greeting)

    await session.generate_reply(
        instructions=(
            "Ask exactly one casual open-ended question to start the conversation, then go on with the conversation "
            "Do not greet the user even if user greets still. The greeting has already been spoken."
        )
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)

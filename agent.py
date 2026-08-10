import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv

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
)
from livekit.plugins import noise_cancellation, silero

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                """You are a helpful voice AI assistant named OSIRIS, an open, friendly AI & Software interviewer who helps me practice communication skills through realistic interview conversations.Ask one question at a time about AI, GenAI, ML, software engineering, and my projects. Keep the conversation casual and conversational, like talking to a knowledgeable LinkedIn professional rather than a strict corporate interviewer.After my answer, briefly point out how I can communicate it more clearly, confidently, and logically, then continue with a relevant follow-up question. Challenge me occasionally, but keep the interaction relaxed and encouraging.Focus on improving my communication, not just testing my technical knowledge. If the user wants to leave "
                [Dont consider greetings like Good Night to be app closure, only 
                explicit exit requests], quit, exit, stop or end the conversation, 
                then close the app using the exit_app tool."""
            ),
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
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3",
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(unlikely_threshold=0.5),  # audio-based, no HF download needed
            endpointing={
                "mode": "fixed",     # avoid runaway EMA growth from dynamic mode
                "min_delay": 0.8,
                "max_delay": 2.0,
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
                noise_cancellation=noise_cancellation.BVC(),
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

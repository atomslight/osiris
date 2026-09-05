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
from livekit.agents.llm import StopResponse
from livekit.plugins import noise_cancellation, silero

load_dotenv()


# ============================================================
# EVENING REFLECTION QUESTIONS
# ============================================================

EVENING_QUESTIONS = [
    "What did you like about today, that you are you proud of accomplishing?",
    "What lessons did you learn today?",
    "What will you do better tomorrow?",
]


# File where only the 3 evening Q&A responses are stored
def get_evening_log_file() -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"evening_reflections_{timestamp}.txt"


# ============================================================
# ASSISTANT
# ============================================================

class Assistant(Agent):
    def __init__(self, evening_mode: bool = False) -> None:

        super().__init__(
            instructions=(
                """You are a communication expert for a realtime conversation.

Your role is to encourage, not discourage. Help the person express their authentic self, build curiosity to speak more openly, and explore their confidence, humility, and communication style.

Pay attention to how clearly and naturally they articulate their thoughts. Encourage concise, understandable responses with clear conclusions rather than unnecessary overexplaining.

Maintain a calm, positive, and supportive presence. Help the person feel more comfortable, confident, and content while communicating."""
            ),
        )

        self.evening_mode = evening_mode

        # Tracks which evening question the user is answering
        # 0 = question 1
        # 1 = question 2
        # 2 = question 3
        self.evening_question_index = 0

        # Stores only the three answers for the current session
        self.evening_answers = []
        self.evening_log_file = get_evening_log_file()
    # ========================================================
    # EVENING QUESTION FLOW
    # ========================================================

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:

        # Normal conversation should behave normally
        if not self.evening_mode:
            return

        user_answer = new_message.text_content.strip()

        # Ignore empty turns
        if not user_answer:
            raise StopResponse()

        current_question_index = self.evening_question_index

        # ----------------------------------------------------
        # Save ONLY answers to the 3 evening questions
        # ----------------------------------------------------

        if current_question_index < len(EVENING_QUESTIONS):
            self.evening_answers.append(user_answer)

            # Save immediately after each answer
            self.save_evening_answer(
                current_question_index,
                user_answer
            )

        # ----------------------------------------------------
        # Question 1 answered
        # ----------------------------------------------------

        if current_question_index == 0:

            self.evening_question_index = 1

            await self.session.say(
                "That's something worth being proud of. "
                f"{EVENING_QUESTIONS[1]}"
            )

            raise StopResponse()

        # ----------------------------------------------------
        # Question 2 answered
        # ----------------------------------------------------

        elif current_question_index == 1:

            self.evening_question_index = 2

            await self.session.say(
                "That's a valuable lesson. "
                f"{EVENING_QUESTIONS[2]}"
            )

            raise StopResponse()

        # ----------------------------------------------------
        # Question 3 answered
        # ----------------------------------------------------

        elif current_question_index == 2:

            # Reflection is complete
            self.evening_question_index = 3

            await self.session.say(
                "That's a great intention for tomorrow."
            )

            raise StopResponse()

    # ========================================================
    # SAVE EVENING ANSWER
    # ========================================================

    def save_evening_answer(
        self,
        question_index: int,
        answer: str
    ) -> None:

        now = datetime.now()

        day = now.strftime("%A")
        date = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        question_number = question_index + 1
        question = EVENING_QUESTIONS[question_index]

        with open(
            self.evening_log_file,
            "a",
            encoding="utf-8"
        ) as file:

            # Add a session header only for question 1
            if question_index == 0:

                file.write("\n")
                file.write("=" * 60 + "\n")
                file.write(f"Day: {day}\n")
                file.write(f"Date: {date}\n")
                file.write(f"Session Started: {timestamp}\n")
                file.write("=" * 60 + "\n")

            file.write(f"\nQuestion {question_number}: {question}\n")
            file.write(f"Timestamp: {timestamp}\n")
            file.write(f"Answer {question_number}: {answer}\n")

            # Mark completion after question 3
            if question_index == 2:
                file.write("\nReflection completed.\n")

    # ========================================================
    # SHUTDOWN / CLOSE FUNCTIONALITY
    # ========================================================

    @function_tool()
    async def exit_app(self, context: RunContext) -> str:
        """
        Close the assistant when the user wants to exit,
        quit, stop, or end the conversation.
        """

        context.disallow_interruptions()

        await self.session.say(
            "Goodbye. Closing the assistant."
        )

        print("Shutting down LiveKit agent...")

        job_ctx = get_job_context()

        job_ctx.shutdown(
            reason="user requested exit"
        )

        await asyncio.sleep(2)

        os._exit(0)

        return "Assistant closed."


# ============================================================
# SERVER
# ============================================================

server = AgentServer()


# ============================================================
# GREETING
# ============================================================

def get_greeting() -> str:

    now = datetime.now()

    hour = now.hour
    minute = now.minute

    if 5 <= hour < 12:
        return "Good Morning"

    elif 12 <= hour < 16:
        return "Good Afternoon"

    elif hour == 16 and minute < 30:
        return "Good Afternoon"

    else:
        return "Good Evening"


# ============================================================
# LIVEKIT SESSION
# ============================================================

@server.rtc_session()
async def entrypoint(ctx: JobContext):

    now = datetime.now()

    # Evening mode starts at exactly 4:30 PM
    evening_mode = (
        now.hour > 16
        or (
            now.hour == 16
            and now.minute >= 30
        )
    )

    assistant = Assistant(
        evening_mode=evening_mode
    )

    session = AgentSession(

        stt="assemblyai/universal-streaming:en",

        llm="openai/gpt-4.1-mini",

        tts="cartesia/sonic-3",

        vad=silero.VAD.load(),

        turn_handling=TurnHandlingOptions(

            turn_detection=inference.TurnDetector(
                unlikely_threshold=0.5
            ),

            endpointing={
                "mode": "fixed",
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

    # ========================================================
    # START SESSION
    # ========================================================

    await session.start(

        agent=assistant,

        room=ctx.room,

        room_options=room_io.RoomOptions(

            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),

        ),
    )

    # ========================================================
    # GREETING
    # ========================================================

    greeting = get_greeting()

    await session.say(greeting)

    # ========================================================
    # EVENING MODE
    # ========================================================

    if evening_mode:

        # Ask ONLY the first question
        await session.say(
            EVENING_QUESTIONS[0]
        )

    # ========================================================
    # NORMAL MODE
    # ========================================================

    else:

        await session.generate_reply(
            instructions=(
                "Ask exactly one casual open-ended question "
                "to start the conversation, then continue naturally. "
                "Do not greet the user. "
                "The greeting has already been spoken."
            )
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO
    )

    agents.cli.run_app(server)

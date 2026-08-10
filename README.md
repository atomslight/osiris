# 🎙️ AiRAA: LiveKit Voice Agent
> **OSIRIS: Your Personal AI Interview Coach**

## 📖 Overview
AiRAA (OSIRIS) is an open, friendly AI and Software interview practice assistant designed to help you hone your communication skills. Instead of rigid, traditional corporate interviews, OSIRIS provides a casual, conversational experience akin to chatting with a knowledgeable LinkedIn professional. It listens to your responses, offers constructive feedback on clarity and confidence, and dynamically generates follow-up questions to challenge and grow your abilities.

## ✨ Features
- **Real-Time Voice Interaction:** Seamless, low-latency audio conversations powered by WebRTC.
- **Intelligent Turn Detection:** Advanced Voice Activity Detection (VAD) ensures the AI knows exactly when you've finished speaking, handling interruptions naturally.
- **Background Noise Cancellation:** Built-in noise suppression keeps the focus strictly on your voice.
- **Smart Interviewing Logic:** Evaluates both your technical knowledge and your communication delivery.
- **Automated Desktop Integration:** Includes a session listener (`session.py`) that can trigger the agent when your computer unlocks.
- **Voice-Command App Exit:** Say "quit," "exit," or "stop," and the assistant gracefully shuts down.

## 🛠 Tech Stack
- **[Python (3.13+)](https://www.python.org/):** The core runtime powering the backend.
- **[LiveKit Agents](https://livekit.io/):** Handles the real-time WebRTC streaming and agent lifecycle.
- **[AssemblyAI](https://www.assemblyai.com/):** High-accuracy Speech-to-Text (STT) for understanding your spoken answers.
- **[OpenAI](https://openai.com/):** The conversational brain (LLM) that powers OSIRIS's responses and feedback.
- **[Cartesia](https://cartesia.ai/):** Ultra-realistic Text-to-Speech (TTS) for natural-sounding AI voice generation.
- **[Silero VAD](https://github.com/snakers4/silero-vad):** Locally-run Voice Activity Detection to handle conversational turn-taking.
- **[uv](https://github.com/astral-sh/uv):** An incredibly fast Python package installer and resolver used to run the project.

## 📋 Prerequisites
Before you begin, ensure you have the following installed and ready:
- **Python:** Version `3.13` or higher.
- **uv:** The fast Python package manager (`pip install uv`).
- **Git:** For cloning the repository.
- **LiveKit Account:** A LiveKit Cloud project (or local server) for WebRTC hosting.
- **API Keys:** You will need valid API keys for:
  - LiveKit (URL, API Key, and Secret)
  - AssemblyAI (`ASSEMBLYAI_API_KEY`)
  - OpenAI (`OPENAI_API_KEY`)
  - Cartesia (`CARTESIA_API_KEY`)

## 🚀 Local Development

Follow these step-by-step instructions to get OSIRIS running on your machine.

### 1. Clone the Repository
Open your terminal and run:
```bash
git clone <your-repository-url>
cd livekit-voice-agent
```

### 2. Install Dependencies
This project uses `uv` for lightning-fast dependency management. Install everything by running:
```bash
uv sync
```
*(If you prefer not to use `uv sync`, you can also create a virtual environment and run `uv pip install .`)*

### 3. Environment Setup
You need to configure your environment variables for the agent to connect to LiveKit and the AI providers.

1. Create a new file named `.env` in the root directory (if there is an `.env.example`, copy it: `cp .env.example .env`).
2. Open `.env` in your text editor and add your credentials:
```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-project-url.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# AI Provider Keys
OPENAI_API_KEY=your_openai_api_key
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
CARTESIA_API_KEY=your_cartesia_api_key
```

### 4. Run the Development Server
With your dependencies installed and `.env` configured, you can launch the voice agent in your terminal:
```bash
uv run agent.py console
```
Once you see the "Agent started" message, OSIRIS will greet you based on the time of day and ask its first interview question.

*Note: Since this is an agent process, there is no separate "build for production" step like a React app. You simply deploy `agent.py` to your production server or container.*

## 🧠 How It Works (Architecture)
1. **Connection:** When `agent.py` runs, it connects to your LiveKit room via WebRTC.
2. **Listening:** Your microphone audio is streamed securely to the server. Noise cancellation (BVC) cleans the audio, and Silero VAD detects when you are speaking versus when you are silent.
3. **Understanding:** Once you stop speaking, the audio chunk is sent to AssemblyAI (STT) to be transcribed into text.
4. **Thinking:** The transcribed text is sent to OpenAI. The AI evaluates your answer, prepares constructive feedback, and formulates the next question.
5. **Speaking:** The AI's text response is streamed to Cartesia (TTS), which generates human-like audio that plays back through your speakers.

## 📁 Folder Structure
Here is a simplified view of the project files and what they do:

```text
livekit-voice-agent/
├── agent.py               # The main brain: Configures LiveKit, AI providers, and the OSIRIS prompt.
├── session.py             # A background listener script to trigger the agent on desktop unlock.
├── .env                   # Your private environment variables (DO NOT COMMIT).
├── pyproject.toml         # Defines the project dependencies and Python version.
├── uv.lock                # Locked dependency tree for deterministic installs.
└── Skills and improvements of AiRAA livekit voice agent.txt # Developer notes on future features.
```
# AiRAA (OSIRIS) Voice Agent
> Your Personal AI Technical Interviewer & Coach

## 📖 Overview
AiRAA is an intelligent, voice-based AI assistant designed to help software engineers and AI practitioners master technical interviews. By leveraging ultra-low latency WebRTC audio, real-time speech-to-text, and advanced language models, it conducts realistic conversational interviews. It dynamically evaluates your answers, provides immediate constructive feedback, and guides you through complex topics like Python, LLMs, RAG, and cloud architecture.

## ✨ Features
- **Real-Time Voice Interaction:** Lightning-fast speech-to-text and text-to-speech interaction for natural conversations.
- **Dynamic Interviewing:** Asks progressive technical questions based on your resume and skillset, digging deeper when answers lack depth.
- **Instant Feedback & Scoring:** Rates your answers on a 1-10 scale, identifies missing points, and provides the "ideal" response.
- **Graceful Interruptions:** Supports natural conversational flow, allowing you to interrupt the AI smoothly using Voice Activity Detection (VAD).
- **Intelligent Context Management:** Remembers conversation history and intelligently manages conversational turns.
- **Voice Commands:** Simply say "quit", "exit", or "stop" to safely and cleanly shut down the application.

## 🛠 Tech Stack
- **Python (v3.13+):** The core programming language powering the application logic.
- **LiveKit Agents:** Manages real-time WebRTC audio streaming, room connections, and orchestration.
- **OpenAI (GPT-4.1 Mini):** The "brain" of the agent, providing intelligent reasoning and technical evaluation.
- **AssemblyAI:** Provides high-accuracy, real-time Speech-to-Text (STT) capabilities.
- **Cartesia (Sonic-3):** Delivers ultra-realistic, conversational Text-to-Speech (TTS) audio generation.
- **Silero VAD:** Detects human speech (Voice Activity Detection) to manage turn-taking and allow interruptions.
- **uv:** An extremely fast Python package and project manager for handling dependencies.

## 📋 Prerequisites
Before you begin, ensure you have the following installed and configured on your machine:
- **Python:** Version 3.13 or higher.
- **uv:** The fast Python package manager (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Git:** For cloning the repository.
- **API Keys:** You will need accounts and active API keys for the following services:
  - **LiveKit Cloud** (URL, API Key, API Secret)
  - **OpenAI** (for the LLM)
  - **AssemblyAI** (for Speech-to-Text)
  - **Cartesia** (for Text-to-Speech)

## 🚀 Local Development (Step-by-Step)

1. **Clone the Repository**
   Open your terminal and clone the project:
   ```bash
   git clone https://github.com/your-username/livekit-voice-agent.git
   cd livekit-voice-agent
   ```

2. **Install Dependencies**
   Since the project uses `uv` for lightning-fast dependency management, simply run:
   ```bash
   uv sync
   ```
   *(This automatically creates an isolated virtual environment and installs everything listed in `pyproject.toml` and `uv.lock`.)*

3. **Environment Setup**
   You need to configure your environment variables. Create a new `.env` file in the root directory (or copy from an example if one exists):
   ```bash
   cp .env.example .env 2>/dev/null || touch .env
   ```

   Open the `.env` file in your favorite text editor and add your LiveKit credentials (found in your LiveKit Cloud dashboard), along with your other required provider keys:
   ```env
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=your_livekit_api_key
   LIVEKIT_API_SECRET=your_livekit_api_secret
   OPENAI_API_KEY=your_openai_api_key
   ASSEMBLYAI_API_KEY=your_assemblyai_api_key
   CARTESIA_API_KEY=your_cartesia_api_key
   ```

4. **Run the Development Server**
   Start the voice agent in console mode:
   ```bash
   uv run agent.py console
   ```
   *(Note: You can connect to this agent using a LiveKit Sandbox frontend or a custom client UI by providing the same LiveKit connection credentials.)*

5. **Build for Production**
   For production deployments (like Docker containers), you can export the locked dependencies to a standard format:
   ```bash
   uv export --format requirements.txt > requirements.txt
   ```
   *(You can then use this `requirements.txt` in a Dockerfile to run the agent in a cloud environment.)*

## 🧠 How It Works (Architecture)
1. **Connection:** When started, the `AgentServer` initializes and connects to a LiveKit room via WebRTC, waiting for a human participant to join.
2. **Listening (STT):** As you speak, Silero VAD detects your voice activity. The raw audio is instantly streamed to AssemblyAI, which transcribes your speech into text.
3. **Reasoning (LLM):** The transcribed text is sent to OpenAI's language model. Acting under strict system prompts, the model evaluates your answer, scores it, formulates constructive feedback, and decides on the next interview question.
4. **Speaking (TTS):** The LLM's text response is passed to Cartesia, which synthesizes it into natural-sounding speech.
5. **Playback & Orchestration:** The generated audio is streamed back through LiveKit into your speakers with built-in noise cancellation. If you interrupt the agent while it's speaking, the turn-detector halts the audio playback instantly to listen to you.

## 📁 Folder Structure
```text
.
├── agent.py                 # Core application logic, agent instructions, and LiveKit orchestration.
├── pyproject.toml           # Project metadata, configuration, and dependencies (managed by uv).
├── uv.lock                  # Lockfile ensuring exact and consistent dependency versions.
├── .env                     # Local environment variables (API keys, URLs).
├── session.py               # Auxiliary logic for session handling and management.
├── browser-automation/      # Scripts for web-based automations or external UI testing.
├── kokoro/                  # Experimental text-to-speech integration scripts (e.g., Kokoro TTS).
└── parakeet/                # Audio processing and local STT experiments (e.g., Parakeet models).
```
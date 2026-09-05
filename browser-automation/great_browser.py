import asyncio
from browser_use import Agent, ChatOllama

async def main():
    # Talks to Ollama's native API directly (default: http://localhost:11434)
    llm = ChatOllama(
        model='llama3.1:8b',
    )

    agent = Agent(
        task="Go to google.com click ai mode and instantly type give me its linkedin profile url Marc Strassman Founder & CEO SenseMaker Voice Los Angeles, CA",
        llm=llm,
    )

    history = await agent.run()

if __name__ == "__main__":
    asyncio.run(main())

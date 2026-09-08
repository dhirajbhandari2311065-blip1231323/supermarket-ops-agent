import asyncio
from app.agent.orchestrator import AgentOrchestrator


async def main():
    agent = AgentOrchestrator()

    print("--- User Input: Check stock of Tata Salt ---")
    reply1 = await agent.process_user_message("How much Tata Salt is left in stock?")
    print(f"Agent Reply:\n{reply1}\n")

    print("--- User Input: Record Suresh Khata credit ---")
    reply2 = await agent.process_user_message("Put 500 rupees on Suresh's khata.")
    print(f"Agent Reply:\n{reply2}\n")

if __name__ == "__main__":
    asyncio.run(main())
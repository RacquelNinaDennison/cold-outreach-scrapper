from agents.nodes.scrapper import run 
from settings import Settings


async def main():
    # Example state slice for the scrapper node
    state = {
        "location": "Cape Town",
        "run_id": "test_run_001"
    }
    
    result = await run(state)
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
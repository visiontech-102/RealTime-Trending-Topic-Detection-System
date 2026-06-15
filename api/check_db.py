import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    db = AsyncIOMotorClient('mongodb://localhost:27017')['trending_topics_db']
    users = await db['users'].find().to_list(100)
    for u in users:
        print(u)

if __name__ == "__main__":
    asyncio.run(run())

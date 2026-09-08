import asyncio
from app.database.connection import init_db, engine

async def main():
    print("Initializing database tables...")
    await init_db()
    print("Database tables initialized successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
"""Create all tables and seed the default admin user."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import connect_db, disconnect_db


async def main():
    await connect_db()
    await disconnect_db()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())

"""Non-interactive check of the NiFi client integration."""

import asyncio
import sys

from app.nifi_client import get_all_processors


async def main() -> None:
    try:
        await get_all_processors()
        print("successfully connect")
    except Exception:
        print("connection failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

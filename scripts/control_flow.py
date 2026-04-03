import argparse
import asyncio
import sys
from app.nifi_client import find_group_by_name, start_process_group, stop_process_group

async def main() -> None:
    parser = argparse.ArgumentParser(description="Start or stop a NiFi process group.")
    parser.add_argument("action", choices=["start", "stop"], help="Action to perform")
    parser.add_argument("name", nargs="+", help="Name of the process group")
    args = parser.parse_args()
    
    name = " ".join(args.name)
    
    try:
        group = await find_group_by_name(name)
        if not group:
            print(f"Group '{name}' not found.")
            return

        group_id = group["id"]
        if args.action == "start":
            print(f"Starting group '{name}' (ID: {group_id})...")
            await start_process_group(group_id)
            print("Successfully started.")
        else:
            print(f"Stopping group '{name}' (ID: {group_id})...")
            await stop_process_group(group_id)
            print("Successfully stopped.")
            
    except Exception as exc:
        print("FAILED:", exc)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

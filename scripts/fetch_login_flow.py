import asyncio
import sys
import json
from app.nifi_client import find_group_by_name, _request

async def main() -> None:
    name = "NiFi_Flow login flow"
    try:
        group = await find_group_by_name(name)
        if not group:
            print(f"Group '{name}' not found.")
            return

        group_id = group["id"]
        print(f"--- Group Details ---")
        print(f"Name: {name}")
        print(f"ID: {group_id}")
        
        # Fetch processors inside this group
        processors = await _request("GET", f"/process-groups/{group_id}/processors")
        print(f"\n--- Processors inside the group ---")
        for proc in processors.get("processors", []):
            comp = proc.get("component", {})
            print(f"Processor Name: {comp.get('name')} | ID: {comp.get('id')} | Type: {comp.get('type')}")
        
    except Exception as exc:
        print("FAILED:", exc)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

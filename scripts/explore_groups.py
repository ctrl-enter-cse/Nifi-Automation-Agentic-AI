import asyncio
import sys
from app.nifi_client import _request

async def main() -> None:
    try:
        # Get child process groups of root
        groups = await _request("GET", "/process-groups/root/process-groups")
        print("Process Groups in Root:")
        for group in groups.get("processGroups", []):
            component = group.get("component", {})
            print(f"ID: {component.get('id')} | Name: {component.get('name')}")
            
        # Also check root group itself just in case
        root = await _request("GET", "/process-groups/root")
        print(f"\nRoot Group Name: {root.get('component', {}).get('name')}")
        
    except Exception as exc:
        print("FAILED:", exc)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

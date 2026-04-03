import asyncio
import sys
import re
from app.nifi_client import create_connection, get_processor
from typing import List

async def link_by_ids(source_id: str, dest_id: str, relationships: List[str]):
    """
    Connects two NiFi processors by their IDs.
    """
    try:
        # 1. Fetch source details to find its group ID
        source_proc = await get_processor(source_id)
        group_id = source_proc.get("component", {}).get("parentGroupId")
        
        if not group_id:
            print(f"FAILED: Could not determine parent group for processor {source_id}")
            return

        print(f"--- Linking Processors in Group {group_id} ---")
        print(f"Source: {source_id}")
        print(f"Dest  : {dest_id}")
        print(f"Rels  : {relationships}")

        # 2. Create the connection
        await create_connection(group_id, source_id, dest_id, relationships)
        print("--- [SUCCESS] Connection Created ---")
        
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    # Expecting: UpdateAttribute (ID) -- "rel" --> ReplaceText (ID)
    if len(sys.argv) < 2:
        print("Usage: python link_processors.py '<COMMAND_STRING>'")
        sys.exit(1)
        
    cmd = " ".join(sys.argv[1:])
    # Regex to extract (ID) -- "rel" --> (ID)
    # Match pattern: (ID_Source) -- "relationship" --> (ID_Dest)
    match = re.search(r'\((P[a-f0-9\-]+)\)\s*--\s*"(.*?)"\s*-->\s*.*?\((P[a-f0-9\-]+)\)', cmd)
    
    if match:
        src_id = match.group(1)
        rel = match.group(2)
        dest_id = match.group(3)
        asyncio.run(link_by_ids(src_id, dest_id, [rel]))
    else:
        # Fallback to simple ID1 ID2 REL
        parts = cmd.split()
        if len(parts) >= 3:
            asyncio.run(link_by_ids(parts[0], parts[1], [parts[2]]))
        else:
            print("FAILED: Could not parse link command. Use format: SourceName (ID) -- 'Relation' --> DestName (ID)")

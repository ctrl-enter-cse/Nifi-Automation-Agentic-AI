import argparse
import asyncio
import json
import sys
from app.nifi_client import (
    find_group_by_name, 
    update_processor_config, 
    stop_processor, 
    start_processor,
    _request
)

async def main() -> None:
    parser = argparse.ArgumentParser(description="Update any NiFi processor's property dynamically.")
    parser.add_argument("processor_name", help="Name of the processor to update")
    parser.add_argument("property_name", help="Name of the property to change")
    parser.add_argument("property_value", help="New value for the property")
    parser.add_argument("--group", default="NiFi_Flow login flow", help="Process group name where the processor exists")
    args = parser.parse_args()
    
    try:
        # 1. Find the Group
        group = await find_group_by_name(args.group)
        if not group:
            print(f"Group '{args.group}' not found.")
            return
            
        group_id = group["id"]
        
        # 2. Find the Processor inside that Group
        processors_data = await _request("GET", f"/process-groups/{group_id}/processors")
        target_proc = None
        for p in processors_data.get("processors", []):
            if p["component"]["name"] == args.processor_name:
                target_proc = p
                break
        
        if not target_proc:
            print(f"Could not find a processor named '{args.processor_name}' in group '{args.group}'.")
            return
            
        proc_id = target_proc["id"]
        
        # 3. Stop the Processor (NiFi requires processors to be stopped to update properties)
        print(f"Stopping processor '{args.processor_name}' (ID: {proc_id})...")
        await stop_processor(proc_id)
        
        # Give NiFi a moment to settle the state
        await asyncio.sleep(2)
        
        # 4. Update the Property
        print(f"Updating '{args.property_name}' to '{args.property_value}'...")
        await update_processor_config(proc_id, {args.property_name: args.property_value})
        print("Property updated successfully.")
        
        # 5. Restart the Processor
        print(f"Restarting processor '{args.processor_name}'...")
        await start_processor(proc_id)
        print(f"Update complete. Processor '{args.processor_name}' is now running with the new config.")
        
    except Exception as exc:
        print("FAILED to update processor:", exc)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

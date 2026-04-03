import asyncio
import sys
from app.nifi_client import (
    find_group_by_name, 
    update_processor_config, 
    stop_process_group, 
    start_process_group,
    _request
)

async def main() -> None:
    group_name = "NiFi_Flow login flow"
    target_port = "7082"
    
    try:
        group = await find_group_by_name(group_name)
        if not group:
            print(f"Group '{group_name}' not found")
            return
            
        group_id = group["id"]
        
        # 1. Stop the group first (processors must be stopped to update properties)
        print(f"Stopping group '{group_name}'...")
        await stop_process_group(group_id)
        
        # Wait for state to settle
        await asyncio.sleep(2)
        
        # 2. Find the 'HandleHttpRequest' processor in this group
        processors_data = await _request("GET", f"/process-groups/{group_id}/processors")
        target_proc = None
        for p in processors_data.get("processors", []):
            if p["component"]["name"] == "HandleHttpRequest":
                target_proc = p
                break
        
        if not target_proc:
            print("Could not find a processor named 'HandleHttpRequest' in the group.")
            return
            
        proc_id = target_proc["id"]
        
        # 3. Update the 'Listening Port' property
        print(f"Updating '{target_proc['component']['name']}' (ID: {proc_id}) port to {target_port}...")
        await update_processor_config(proc_id, {"Listening Port": target_port})
        print("Property updated successfully.")
        
        # 4. Restart the group
        print(f"Restarting group '{group_name}'...")
        await start_process_group(group_id)
        print("Flow is back online with the new port configuration.")
        
    except Exception as exc:
        print("FAILED to update port:", exc)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

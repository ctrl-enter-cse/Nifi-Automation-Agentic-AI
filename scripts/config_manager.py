import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.nifi_client import find_group_by_name, _request, get_connections
from scripts.intent_utils import api_data_to_mermaid

CONFIG_DIR = "configs"

def get_latest_snapshot(group_name: str) -> Optional[Dict[str, Any]]:
    """Find the most recent JSON file for the given group."""
    if not os.path.exists(CONFIG_DIR):
        return None
    
    files = [f for f in os.listdir(CONFIG_DIR) if f.startswith(group_name.replace(" ", "_")) and f.endswith(".json")]
    if not files:
        return None
    
    latest_file = sorted(files)[-1]
    with open(os.path.join(CONFIG_DIR, latest_file), "r") as f:
        return json.load(f)

async def fetch_current_config(group_id: str) -> Dict[str, Any]:
    """Fetch the full, raw Process Group blueprint (Download)."""
    # The /download endpoint returns the complete flow definition (blueprint)
    return await _request("GET", f"/process-groups/{group_id}/download")

def diff_configs(old_config: Dict, new_config: Dict):
    """Compare two configurations and print differences."""
    all_procs = set(old_config.keys()) | set(new_config.keys())
    
    print("\n" + "="*40)
    print("--- CONFIG DIFFERENCES ---")
    print("="*40)
    
    changes_found = False
    for proc in sorted(all_procs):
        if proc not in old_config:
            print(f"[+] NEW Processor: {proc}")
            changes_found = True
        elif proc not in new_config:
            print(f"[-] REMOVED Processor: {proc}")
            changes_found = True
        else:
            p_old = old_config[proc]["properties"]
            p_new = new_config[proc]["properties"]
            
            proc_changes = []
            for k, v in p_new.items():
                old_v = p_old.get(k)
                if old_v != v:
                    proc_changes.append(f"  * [{k}]: {old_v} -> {v}")
            
            if proc_changes:
                print(f"\nProcessor: {proc}")
                for change in proc_changes:
                    print(change)
                changes_found = True
                
    if not changes_found:
        print("No differences found between live config and snapshot.")
    print("="*40 + "\n")

async def main() -> None:
    parser = argparse.ArgumentParser(description="NiFi Configuration Manager (Snapshots & Diffs)")
    parser.add_argument("action", choices=["snapshot", "details", "diff"], help="Action to perform")
    parser.add_argument("name", nargs="+", help="Name of the process group")
    args = parser.parse_args()
    
    group_name = " ".join(args.name)
    
    try:
        group = await find_group_by_name(group_name)
        if not group:
            print(f"Group '{group_name}' not found.")
            return

        group_id = group["id"]
        current_config = await fetch_current_config(group_id)

        if args.action == "details":
            # 1. Fetch connections for Mermaid
            c_data = await get_connections(group_id)
            connections = [c.get("component", {}) for c in c_data.get("connections", [])]
            
            # 2. Extract processors list from download data
            # Note: The download API returns a different structure than the direct processors API
            # but usually it's in flow -> processors
            processors = current_config.get("flow", {}).get("processors", [])
            
            print(f"\n--- [Token-Efficient Context] Group: {group_name} ---")
            print("\n### Flow Structure (Mermaid) ###")
            print(api_data_to_mermaid(processors, connections, simplified=True))
            
            print("\n### Processor Configuration Summary ###")
            for p in processors:
                comp = p.get("component", {})
                name = comp.get("name")
                print(f"\n[{name}]")
                props = comp.get("config", {}).get("properties", {})
                for k, v in props.items():
                    if v: # Only show non-empty properties to save tokens
                        print(f"  - {k}: {v}")
        
        elif args.action == "snapshot":
            if not os.path.exists(CONFIG_DIR):
                os.makedirs(CONFIG_DIR)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{group_name.replace(' ', '_')}_{timestamp}.json"
            filepath = os.path.join(CONFIG_DIR, filename)
            
            with open(filepath, "w") as f:
                json.dump(current_config, f, indent=2)
            print(f"Snapshot saved to: {filepath}")

        elif args.action == "diff":
            old_config = get_latest_snapshot(group_name)
            if not old_config:
                print(f"No previous snapshot found for '{group_name}'. Take a snapshot first.")
                return
            
            diff_configs(old_config, current_config)
            
    except Exception as exc:
        print("FAILED to manage config:", exc)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

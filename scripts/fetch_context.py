import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List

# Core NiFi Client for live data
from app.nifi_client import _request, find_group_by_name, get_connections
# Reuse our new Mermaid converter
from scripts.fetch_group import generate_html
from scripts.intent_utils import api_data_to_mermaid, get_intent_schema

async def fetch_llm_context(group_name: str, visualize: bool = False) -> None:
    """
    Fetches the flow from NiFi and extracts a token-efficient Mermaid context for the LLM.
    Ensures that the full JSON is never sent directly to the LLM.
    """
    try:
        # 1. Locate the Group
        group = await find_group_by_name(group_name)
        if not group:
            print(f"ERROR: Process Group '{group_name}' not found.")
            return

        group_id = group["id"]
        
        # 2. Fetch Processors and Connections
        p_data = await _request("GET", f"/process-groups/{group_id}/processors")
        c_data = await get_connections(group_id)
        
        processors = p_data.get("processors", [])
        connections = c_data.get("connections", [])
        
        # 3. Direct Conversion to Simplified Mermaid (No intermediate JSON sent to LLM)
        mermaid_context = api_data_to_mermaid(processors, [c.get("component", {}) for c in connections], simplified=True)
        
        # 4. Handle Visualizer
        if visualize:
            viz_file = f"{group_name.replace(' ', '_')}_viz.html"
            print(f"[INFO] Generating premium visualization to '{viz_file}'...")
            html = generate_html(group_name, processors, [c.get("component", {}) for c in connections])
            with open(viz_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[SUCCESS] '{viz_file}' created. Original templates remain untouched.")

        # 5. Final Minimal Context for LLM
        print("\n" + "="*80)
        print("--- LLM INTENT CONTEXT (Minimal & Token-Efficient) ---")
        print("\nUse this graph to identify the processor and property you wish to modify:")
        print("="*80)
        print(mermaid_context)
        print("="*80)
        
        print("\n### Task Schema ###")
        print("Return ONLY a JSON object in this format:")
        print(get_intent_schema())
        print("\n" + "="*80)
        
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch token-efficient LLM context from NiFi.")
    parser.add_argument("name", nargs="+", help="Name of the process group to fetch context for")
    parser.add_argument("--visual", action="store_true", help="Generate 'flow_viz.html' visualization")
    args = parser.parse_args()
    
    name = " ".join(args.name)
    asyncio.run(fetch_llm_context(name, visualize=args.visual))

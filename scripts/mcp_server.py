import asyncio
import os
import sys
import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Ensure the project root is in the path regardless of where the script is called from
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from app.nifi_client import (
    find_group_by_name,
    get_all_processors,
    _request,
    start_process_group,
    stop_process_group,
    update_processor_config,
    stop_processor,
    start_processor,
    get_connections,
    find_processors_by_criteria,
)
from scripts.flow_generator import deploy_flow
from scripts.fetch_group import generate_html
from scripts.intent_utils import api_data_to_mermaid, get_intent_schema

mcp = FastMCP("NiFi-AI-Agent")

@mcp.tool()
async def check_nifi_connection() -> str:
    """Verifies the connection to the Apache NiFi instance."""
    try:
        await get_all_processors()
        return "Successfully connected to Apache NiFi."
    except Exception as e:
        return f"Connection failed: {e}"

@mcp.tool()
async def list_groups() -> str:
    """Lists all process groups in the NiFi root."""
    try:
        groups = await _request("GET", "/process-groups/root/process-groups")
        output = ["Process Groups in NiFi:"]
        for group in groups.get("processGroups", []):
            comp = group.get("component", {})
            output.append(f"- Name: {comp.get('name')} (ID: {comp.get('id')})")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing groups: {e}"

@mcp.tool()
async def get_group_details(group_name: str, visualize: bool = True) -> str:
    """Fetches a token-efficient visual representation (Mermaid) of a process group.
    Use this to understand the flow structure without fetching massive JSON data.
    """
    try:
        group = await find_group_by_name(group_name)
        if not group:
            return f"Group '{group_name}' not found."
        
        group_id = group["id"]
        processors_data = await _request("GET", f"/process-groups/{group_id}/processors")
        processors_list = processors_data.get("processors", [])
        
        connections_data = await get_connections(group_id)
        connections_list = [c.get("component", {}) for c in connections_data.get("connections", [])]
        
        # Build Mermaid Context
        mermaid_graph = api_data_to_mermaid(processors_list, connections_list, simplified=True)
        
        output = [
            f"Terminal: [NiFi-Agent] Fetching group details for '{group_name}'...",
            f"Terminal: [NiFi-Agent] Found {len(processors_list)} processors.",
            "\n--- SIMPLIFIED GRAPH ---",
            mermaid_graph,
            "\n--- Processors inside the group ---"
        ]
        
        for p in processors_list:
            comp = p.get("component", {})
            p_id = comp.get('id')
            p_name = comp.get('name')
            output.append(f"[{p_name}] | ID: {p_id} | Type: {comp.get('type')}")

        if visualize:
            html = generate_html(group_name, processors_list, connections_data.get("connections", []))
            with open("flow_viz.html", "w", encoding="utf-8") as f:
                f.write(html)
            output.append("\n[INFO] 'flow_viz.html' updated.")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching details: {e}"

@mcp.tool()
async def deploy_new_flow(curl_command: str) -> str:
    """Deploys a new NiFi flow based on a provided CURL command.
    Example: curl -X POST https://api.example.com -d '{"key": "val"}'
    """
    try:
        await deploy_flow(curl_command)
        return f"Successfully deployed flow from curl command. Check NiFi for the new 'Logic_Dummy' group."
    except Exception as e:
        return f"Deployment failed: {e}"

@mcp.tool()
async def control_flow(group_name: str, action: str) -> str:
    """Starts or Stops a process group. Action must be 'start' or 'stop'."""
    try:
        group = await find_group_by_name(group_name)
        if not group:
            return f"Group '{group_name}' not found."
        
        if action.lower() == "start":
            await start_process_group(group["id"])
            return f"Started group '{group_name}'."
        elif action.lower() == "stop":
            await stop_process_group(group["id"])
            return f"Stopped group '{group_name}'."
        else:
            return "Invalid action. Use 'start' or 'stop'."
    except Exception as e:
        return f"Control failed: {e}"

@mcp.tool()
async def get_processor_config(
    group_name: str, 
    processor_name: str,
    after_processor: Optional[str] = None,
    before_processor: Optional[str] = None,
    relationship: Optional[str] = None,
    property_key: Optional[str] = None,
    property_value: Optional[str] = None
) -> str:
    """Fetches the detailed configuration (properties) of a single processor.
    If multiple processors match the name, use after_processor/before_processor/relationship or property_key/property_value to narrow it down.
    If no filters are provided and multiple exist, a summary of all matching processors is returned.
    """
    try:
        group = await find_group_by_name(group_name)
        if not group:
            return f"Terminal: [NiFi-Agent] ERROR: Flow/Group '{group_name}' not found."
            
        prop_filters = None
        if property_key and property_value:
            prop_filters = {property_key: property_value}

        candidates = await find_processors_by_criteria(
            group["id"], 
            processor_name, 
            after_processor=after_processor,
            before_processor=before_processor,
            relationship=relationship,
            property_filters=prop_filters
        )
        
        if not candidates:
            return f"Terminal: [NiFi-Agent] ERROR: No processor named '{processor_name}' found in group '{group_name}' with the given criteria."
            
        if len(candidates) > 1:
            output = [f"Terminal: [NiFi-Agent] Found {len(candidates)} processors matching '{processor_name}'. Please be more specific (e.g., provide after_processor)."]
            for p in candidates:
                comp = p.get("component", {})
                output.append(f"- ID: {comp.get('id')} | Type: {comp.get('type')} | State: {comp.get('state')}")
            return "\n".join(output)
            
        target_proc = candidates[0]
        comp = target_proc["component"]
        config = comp.get("config", {})
        properties = config.get("properties", {})
        
        output = [
            f"Terminal: [NiFi-Agent] Configuration for '{processor_name}' in '{group_name}'",
            f"ID: {comp.get('id')}",
            f"Type: {comp.get('type')}",
            f"State: {comp.get('state')}",
            "\n### Properties ###"
        ]
        
        for k, v in properties.items():
            if v is not None:
                output.append(f"  - {k}: {v}")
                
        return "\n".join(output)
    except Exception as e:
        return f"Terminal: [NiFi-Agent] ERROR: Config fetch failed: {e}"

@mcp.tool()
async def update_processor_property(
    group_name: str, 
    processor_name: str, 
    property_name: str, 
    property_value: str,
    after_processor: Optional[str] = None,
    relationship: Optional[str] = None
) -> str:
    """Updates any property of a NiFi processor. 
    Use after_processor/relationship if multiple processors have the same name.
    """
    try:
        group = await find_group_by_name(group_name)
        if not group:
            return f"Group '{group_name}' not found."
            
        candidates = await find_processors_by_criteria(
            group["id"], 
            processor_name, 
            after_processor=after_processor,
            relationship=relationship
        )
        
        if not candidates:
            return f"ERROR: Processor '{processor_name}' not found with the given criteria."
            
        if len(candidates) > 1:
            return f"ERROR: Multiple processors match '{processor_name}'. Found {len(candidates)} matches. Please provide after_processor or relationship to be specific."
            
        target_proc = candidates[0]
        proc_id = target_proc["id"]
        
        await stop_processor(proc_id)
        await asyncio.sleep(1.5) 
        await update_processor_config(proc_id, {property_name: property_value})
        await start_processor(proc_id)
        
        return f"Successfully updated '{property_name}' to '{property_value}' for processor '{processor_name}' (ID: {proc_id})."
    except Exception as e:
        return f"Update failed: {e}"

@mcp.tool()
async def get_group_config_details(group_name: str) -> str:
    """Fetches the full JSON blueprint (download) of a process group."""
    try:
        group = await find_group_by_name(group_name)
        if not group:
            return f"Group '{group_name}' not found."
        
        details = await _request("GET", f"/process-groups/{group['id']}/download")
        return json.dumps(details, indent=2)
    except Exception as e:
        return f"Error fetching config: {e}"

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        print("Starting MCP server with SSE transport on port 8000...")
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    else:
        mcp.run()

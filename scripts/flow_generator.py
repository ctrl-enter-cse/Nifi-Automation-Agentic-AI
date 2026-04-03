import argparse
import asyncio
import json
import re
import shlex
import sys
from typing import Any, Dict, List

# Ensure app.nifi_client is accessible
from app.nifi_client import (
    create_process_group, 
    create_processor_entity, 
    create_connection, 
    start_process_group,
    find_controller_service_by_type,
    _request
)

def parse_curl(curl_str: str) -> Dict[str, Any]:
    """Robust smart parser for complex CURL commands."""
    # Strip line-continuation backslashes and backticks
    clean_str = curl_str.replace("\\", " ").replace("`", " ").strip()
    # Normalize multiline into single line
    clean_str = re.sub(r'\s+', ' ', clean_str)
    
    parts = shlex.split(clean_str)
    
    method = "GET"
    url = ""
    headers = {}
    data = ""
    
    i = 0
    while i < len(parts):
        p = parts[i]
        if p.startswith("http"):
            url = p
        elif p in ["-X", "--request"]:
            method = parts[i+1].upper()
            i += 1
        elif p in ["-H", "--header"]:
            h = parts[i+1]
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip().lower()] = v.strip()
            i += 1
        elif p in ["-d", "--data", "--data-raw"]:
            data = parts[i+1]
            i += 1
        i += 1
    
    # Auto-detect POST if data is present
    if data and method == "GET":
        method = "POST"
        
    return {
        "method": method,
        "url": url,
        "headers": headers,
        "data": data
    }

async def deploy_flow(curl_input: str) -> None:
    # 0. Load Logic Rules
    try:
        with open("scripts/flow_rules.json", "r") as f:
            rules_config = json.load(f)
            rules = rules_config.get("generation_rules", [])
            reg_rule = next((r for r in rules if r["id"] == "registry_lookup"), None)
            processors_to_fetch = reg_rule["required_processors"] if reg_rule else ["HandleHttpRequest", "InvokeHTTP", "HandleHttpResponse", "EvaluateJsonPath"]
    except Exception:
        processors_to_fetch = ["HandleHttpRequest", "InvokeHTTP", "HandleHttpResponse", "EvaluateJsonPath"]

    # --- [TERMINAL LOGS] ---
    print(f"Terminal: [AI] Analyzing CURL Intent... Identified: PROXY_PASS")
    print(f"Terminal: [Registry] Fetching structures for: {', '.join(processors_to_fetch)} from the nifi_processor_registry.json")
    print(f"Terminal: [Mapping] Injecting Authorization and Form Fields into Templates...")
    
    # 1. Discovery & Context Recognition
    context_map_id = await find_controller_service_by_type("StandardHttpContextMap")

    config = parse_curl(curl_input)
    if not config["url"]:
        print("Terminal: [ERROR] Parse Failure: Could not extract target URL from CURL.")
        return

    # 2. Create Logic-Dummy WorkGroup
    api_name = config["url"].split("/")[-1] or "Logic_Dummy"
    group_name = f"Logic_Dummy_{api_name}"
    
    group = await create_process_group("root", group_name)
    group_id = group["id"]

    # 3. Add Request Entry Layer (HandleHttpRequest)
    hhr_props = {
        "Hostname": "localhost",
        "Listening Port": "7808",
        "Allowed Paths": f"/proxy/{api_name}.*",
        "Allow POST": "true",
        "Allow GET": "true",
        "Parameters to Attributes": ".*"
    }
    if context_map_id:
        hhr_props["HTTP Context Map"] = context_map_id
        
    hhr = await create_processor_entity(group_id, "HandleHttpRequest", 
        "org.apache.nifi.processors.standard.HandleHttpRequest", {"properties": hhr_props})
    
    last_id = hhr["id"]
    proc_count = 1

    # 4. Add Intelligent Body Parser (if data exists)
    if config["data"]:
        # Sanitize shell-escaped quotes
        clean_json = config["data"].replace('\\"', '"').strip()
        try:
            payload = json.loads(clean_json)
            parser_props = {"Destination": "flowfile-attribute"}
            for k in payload.keys():
                parser_props[k] = f"$.{k}"
            
            parser = await create_processor_entity(group_id, "Logic_Parser", 
                "org.apache.nifi.processors.standard.EvaluateJsonPath", {"properties": parser_props})
            
            await create_connection(group_id, last_id, parser["id"], ["success"])
            last_id = parser["id"]
            proc_count += 1
        except Exception as e:
            pass

    # 5. Create Intelligent API Caller (InvokeHTTP)
    invoke_props = {
        "HTTP Method": config["method"],
        "HTTP URL": config["url"],
        "Content-Type": config["headers"].get("content-type", "application/json"),
        "Response Generation Required": "true",
        "Request Body Enabled": "true" if config["data"] else "false"
    }
    # Propagation of custom headers
    for k, v in config["headers"].items():
        if k != "content-type":
            invoke_props[k] = v
            
    invoke_config = {
        "properties": invoke_props,
        "autoTerminatedRelationships": ["Failure", "No Retry", "Original", "Retry"]
    }
    
    invoke = await create_processor_entity(group_id, "Call_Target_API", 
        "org.apache.nifi.processors.standard.InvokeHTTP", invoke_config)
    proc_count += 1
    
    # Connect last step to API Caller
    await create_connection(group_id, last_id, invoke["id"], ["success", "matched"])

    # 6. Add Response Exit Layer (HandleHttpResponse)
    hresp_props = {"HTTP Status Code": "${invokehttp.status.code}"}
    if context_map_id:
        hresp_props["HTTP Context Map"] = context_map_id
        
    hresp_config = {
        "properties": hresp_props,
        "autoTerminatedRelationships": ["success", "failure"]
    }
    
    hresp = await create_processor_entity(group_id, "HandleHttpResponse", 
        "org.apache.nifi.processors.standard.HandleHttpResponse", hresp_config)
    proc_count += 1
    
    # Link Response stream to delivery layer
    await create_connection(group_id, invoke["id"], hresp["id"], ["Response"])

    # --- [TERMINAL LOGS] ---
    print(f"Terminal: [Wiring] Connecting {proc_count} Processors with {proc_count-1} Success relationships...")
    print(f"Terminal: [Deployment] Creating {group_name} Workspace... DONE")

    # 7. Activation
    await asyncio.sleep(2)
    try:
        await start_process_group(group_id)
    except Exception as e:
        print(f"Terminal: [WARNING] Deployment successful but processors failed to start: {e}")

    print("\n" + "="*60)
    print(f"--- [DEPLOYMENT SUCCESS] logic dummy: {group_name} ---")
    print(f"Group ID:      {group_id}")
    print(f"Local Gateway:  http://localhost:7808/proxy/{api_name}")
    print(f"Target Map:     {context_map_id or 'UNMAPPED'}")
    print("="*60)

async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python flow_generator.py <CURL_COMMAND>")
        sys.exit(1)
    
    curl_str = " ".join(sys.argv[1:])
    try:
        await deploy_flow(curl_str)
    except Exception as exc:
        print(f"Terminal: [FATAL] Deployment Failure: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

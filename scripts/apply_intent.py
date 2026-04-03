import json
import argparse
import sys
from typing import Dict, Any, Optional

def find_processor_by_name(flow_json: Dict[str, Any], processor_name: str) -> Optional[Dict[str, Any]]:
    """
    Search recursively in the NiFi JSON for a processor with the given name.
    Supports standard NiFi structure and simplified project structure.
    """
    # 1. Check project's simplified structure: {"processors": {"Name": {...}}}
    if "processors" in flow_json and isinstance(flow_json["processors"], dict):
        if processor_name in flow_json["processors"]:
            return flow_json["processors"][processor_name]
    
    # 2. Check standard NiFi processGroupFlow structure
    if "processGroupFlow" in flow_json:
        flow = flow_json["processGroupFlow"]
        for processor in flow.get("flow", {}).get("processors", []):
            if processor.get("component", {}).get("name") == processor_name:
                return processor

    # 3. Check list of processor entities structure
    if "processors" in flow_json and isinstance(flow_json["processors"], list):
        for processor in flow_json["processors"]:
            if processor.get("component", {}).get("name") == processor_name:
                return processor
                
    return None

def apply_modification(flow_json: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a specific intent (processorName, property, value) to a NiFi JSON object.
    Supports standard NiFi structure and simplified project structure.
    """
    target_name = intent.get("processorName")
    target_prop = intent.get("property")
    target_val = intent.get("value")
    
    if not target_name or not target_prop:
        print(f"ERROR: Intent missing fields (processorName, property).")
        return flow_json
    
    # Locate the processor
    processor = find_processor_by_name(flow_json, target_name)
    if not processor:
        print(f"ERROR: Processor '{target_name}' not found.")
        return flow_json
        
    print(f"--- [Applying Intent] ---")
    print(f"Target: {target_name}")
    print(f"Property: {target_prop} -> {target_val}")
    
    # Case A: Project simplified structure
    if "properties" in processor:
        processor["properties"][target_prop] = target_val
        
    # Case B: Standard NiFi structure
    elif "component" in processor and "config" in processor["component"]:
        config = processor["component"]["config"]
        if "properties" not in config:
            config["properties"] = {}
        config["properties"][target_prop] = target_val
        
    return flow_json

def main():
    parser = argparse.ArgumentParser(description="Modify NiFi flow JSON using an Intent JSON.")
    parser.add_argument("flow_file", help="Path to the original NiFi JSON flow file")
    parser.add_argument("intent_file", help="Path to the Intent JSON file (e.g., {'processorName': '...', 'property': '...', 'value': '...'})")
    parser.add_argument("--output", "-o", help="Path to save the modified JSON")
    
    args = parser.parse_args()
    
    try:
        with open(args.flow_file, "r", encoding="utf-8") as f:
            flow_data = json.load(f)
            
        with open(args.intent_file, "r", encoding="utf-8") as f:
            intent_data = json.load(f)
            
        modified_data = apply_modification(flow_data, intent_data)
        
        output_path = args.output or args.flow_file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(modified_data, f, indent=2)
            
        print(f"--- [SUCCESS] ---")
        print(f"Modification saved to: {output_path}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import json
import os

def extract_unique_processors(input_file, output_file):
    # Mapping of common processors found in the working JSON to their standard relationships
    # This is based on NiFi's default processor definitions for 2.7.2
    standard_relationships = {
        "org.apache.nifi.processors.standard.InvokeHTTP": ["Response", "Retry", "No Retry", "Original", "Failure"],
        "org.apache.nifi.processors.standard.HandleHttpRequest": ["success"],
        "org.apache.nifi.processors.standard.HandleHttpResponse": ["success", "failure"],
        "org.apache.nifi.processors.standard.EvaluateJsonPath": ["success", "failure", "unmatched"],
        "org.apache.nifi.processors.standard.ReplaceText": ["success", "failure"],
        "org.apache.nifi.processors.standard.UpdateAttribute": ["success"],
        "org.apache.nifi.processors.standard.ExtractText": ["success", "unmatched"],
        "org.apache.nifi.processors.standard.RouteOnAttribute": ["unmatched"], # Dynamic ones based on user properties
        "org.apache.nifi.processors.standard.LogAttribute": ["success"]
    }

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
            
        processors = flow_data.get("processors", [])
        # Also check inside process groups if any
        for pg in flow_data.get("processGroups", []):
            processors.extend(pg.get("processors", []))

        registry = {}

        for proc in processors:
            proc_type = proc.get("type")
            if proc_type not in registry:
                # Capture the "DNA" of this unique processor
                registry[proc_type] = {
                    "processor_name": proc.get("name"),
                    "type": proc_type,
                    "bundle": proc.get("bundle"),
                    "available_relationships": standard_relationships.get(proc_type, []),
                    "default_properties": proc.get("properties", {}),
                    "property_descriptors": proc.get("propertyDescriptors", {})
                }

        # Save to the formal registry file
        with open(output_file, 'w', encoding='utf-8') as out:
            json.dump(registry, out, indent=2)
            
        print(f"--- [REGISTRY BUILD SUCCESS] ---")
        print(f"File: {output_file}")
        print(f"Unique Processors Found: {len(registry)}")
        for pt in registry.keys():
            print(f" - {pt.split('.')[-1]}")

    except Exception as e:
        print(f"Error extracting registry: {e}")

if __name__ == "__main__":
    # Paths based on project structure
    input_path = r"c:\Users\prasa\scoreMe\nifi-Ai-Agent\workingnififlow.json"
    output_path = r"c:\Users\prasa\scoreMe\nifi-Ai-Agent\nifi_processor_registry.json"
    extract_unique_processors(input_path, output_path)

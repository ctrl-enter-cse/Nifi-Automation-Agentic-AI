import json
from typing import List, Dict, Any

def api_data_to_mermaid(processors: List[Dict[str, Any]], connections: List[Dict[str, Any]], simplified: bool = True) -> str:
    """
    Converts NiFi API processor and connection data to a Mermaid graph.
    Matches the user-requested format: Name (ID) -- "Relation" --> Name (ID)
    """
    nodes = {}
    graph_lines = []
    
    # 1. Map IDs to Names
    for proc in processors:
        comp = proc.get("component", {})
        p_name = comp.get("name", "Unknown")
        p_id = comp.get("id")
        # Store for relationship building
        nodes[p_id] = p_name
        
        # Define the node with its label: VarName["Name (ID)"]
        var_name = p_name.replace(" ", "_").replace("-", "_") + f"_{p_id[:4]}"
        nodes[p_id + "_var"] = var_name
        graph_lines.append(f'    {var_name}["{p_name} ({p_id})"]')

    # 2. Build Relationships
    for conn in connections:
        comp = conn.get("component", {})
        src_id = comp.get("source", {}).get("id")
        dest_id = comp.get("destination", {}).get("id")
        
        # Support both wrapped and unwrapped connection objects
        if not src_id: # Might be in sourceId/destinationId fields in some API responses
            src_id = comp.get("sourceId")
            dest_id = comp.get("destinationId")

        rels = ", ".join(comp.get("selectedRelationships", []))
        
        src_var = nodes.get(src_id + "_var", f"P{src_id}")
        dest_var = nodes.get(dest_id + "_var", f"P{dest_id}")
        
        if rels:
            graph_lines.append(f'    {src_var} -- "{rels}" --> {dest_var}')
        else:
            graph_lines.append(f'    {src_var} --> {dest_var}')

    return "graph TD\n" + "\n".join(graph_lines)

def get_intent_schema() -> str:
    """Returns the schema the LLM should follow for intent extraction."""
    return json.dumps({
        "processorName": "string (the name of the processor to modify)",
        "property": "string (the name of the configuration property)",
        "value": "string (the new value to set)"
    }, indent=2)

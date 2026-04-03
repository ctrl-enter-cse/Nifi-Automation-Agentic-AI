import re
from typing import Optional

def extract_mermaid(html_content: str) -> Optional[str]:
    """
    Extracts the Mermaid graph block from a NiFi Flow Visualizer HTML file.
    Equivalent to the Java logic provided in the strategy.
    """
    start_tag = '<pre class="mermaid">'
    end_tag = '</pre>'
    
    start_idx = html_content.find(start_tag)
    end_idx = html_content.find(end_tag, start_idx)
    
    if start_idx == -1 or end_idx == -1:
        return None
        
    length = len(start_tag)
    return html_content[start_idx + length:end_idx].strip()

def simplify_mermaid(mermaid_graph: str) -> str:
    """
    Simplifies the mermaid graph into the user-requested format:
    Name (ID) -- "Relation" --> Name (ID)
    """
    lines = mermaid_graph.split('\n')
    nodes = {}
    graph_lines = []
    
    # 1. First Pass: Map IDs to Full Names
    # Pattern: P[id]["Name"]
    for line in lines:
        match = re.search(r'(P[a-f0-9\-]+)\["(.*?)"\]', line)
        if match:
            node_id = match.group(1)
            full_name = match.group(2)
            nodes[node_id] = full_name
            
    # 2. Second Pass: Reconstruct Relationships
    for line in lines:
        # Check for relationship pattern: ID1 -- "rel" --> ID2 or ID1 --> ID2
        rel_match = re.search(r'(P[a-f0-9\-]+)\s*(--\s*".*?"\s*-->|-->)\s*(P[a-f0-9\-]+)', line)
        if rel_match:
            id1 = rel_match.group(1)
            arrow = rel_match.group(2)
            id2 = rel_match.group(3)
            
            name1 = nodes.get(id1, id1)
            name2 = nodes.get(id2, id2)
            
            # Format: Name (ID) -- "Rel" --> Name (ID)
            graph_lines.append(f'    {name1} ({id1}) {arrow} {name2} ({id2})')
            
    if not graph_lines:
        return "No relationships found."
        
    return "graph TD\n" + "\n".join(graph_lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python mermaid_parser.py <path_to_html>")
        sys.exit(1)
        
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        html = f.read()
        
    mermaid = extract_mermaid(html)
    if mermaid:
        print("--- EXTRACTED MERMAID ---")
        print(mermaid)
        print("\n--- SIMPLIFIED GRAPH ---")
        print(simplify_mermaid(mermaid))
    else:
        print("No mermaid graph found in HTML.")

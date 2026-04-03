from typing import Any, Optional, List, Dict

import httpx

from .config import settings

CLIENT_ID = "nifi-ai-agent"
_TOKEN: Optional[str] = None


async def _get_token() -> str:
    global _TOKEN
    if _TOKEN:
        return _TOKEN

    base_url = str(settings.nifi_url).rstrip("/")
    auth_url = f"{base_url}/access/token"
    # NiFi token endpoint expects form-encoded data
    data = {"username": settings.nifi_username, "password": settings.nifi_password}

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(auth_url, data=data)
        response.raise_for_status()
        _TOKEN = response.text.strip()
        return _TOKEN


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    base_url = str(settings.nifi_url).rstrip("/")
    url = f"{base_url}{path}"
    timeout = httpx.Timeout(30.0, read=60.0)

    token = await _get_token()
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    kwargs["headers"] = headers

    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
        response = await client.request(method, url, **kwargs)
        if response.status_code == 401:
            # Token might be expired, clear and retry once
            global _TOKEN
            _TOKEN = None
            token = await _get_token()
            headers["Authorization"] = f"Bearer {token}"
            response = await client.request(method, url, **kwargs)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"ERROR: {exc.response.text}")
            raise

        if response.text:
            return response.json()
        return {}


async def get_process_group(group_id: str) -> Any:
    return await _request("GET", f"/process-groups/{group_id}")


async def find_group_by_name(name: str) -> Optional[dict[str, Any]]:
    groups = await _request("GET", "/process-groups/root/process-groups")
    for group in groups.get("processGroups", []):
        if group.get("component", {}).get("name") == name:
            return group
    return None


async def get_connections(group_id: str) -> Any:
    return await _request("GET", f"/process-groups/{group_id}/connections")


async def get_all_processors() -> Any:
    return await _request("GET", "/process-groups/root/processors")


async def get_processor(processor_id: str) -> Any:
    return await _request("GET", f"/processors/{processor_id}")


async def _get_revision(processor_id: str) -> dict[str, Any]:
    processor = await get_processor(processor_id)
    return processor.get("revision", {"version": 0, "clientId": CLIENT_ID})


async def update_run_status(processor_id: str, state: str) -> Any:
    revision = await _get_revision(processor_id)
    payload = {
        "revision": revision,
        "state": state,
        "disconnectedNodeAcknowledged": False,
    }

    return await _request("PUT", f"/processors/{processor_id}/run-status", json=payload)


async def start_processor(processor_id: str) -> Any:
    return await update_run_status(processor_id, "RUNNING")


async def stop_processor(processor_id: str) -> Any:
    return await update_run_status(processor_id, "STOPPED")


async def _get_group_revision(group_id: str) -> dict[str, Any]:
    group = await get_process_group(group_id)
    return group.get("revision", {"version": 0, "clientId": CLIENT_ID})


async def update_group_run_status(group_id: str, state: str) -> Any:
    payload = {
        "id": group_id,
        "state": state,
        "disconnectedNodeAcknowledged": False,
    }
    return await _request("PUT", f"/flow/process-groups/{group_id}", json=payload)


async def start_process_group(group_id: str) -> Any:
    return await update_group_run_status(group_id, "RUNNING")


async def stop_process_group(group_id: str) -> Any:
    return await update_group_run_status(group_id, "STOPPED")


async def create_process_group(parent_id: str, name: str) -> Any:
    payload = {
        "revision": {"version": 0, "clientId": CLIENT_ID},
        "component": {
            "name": name,
            "position": {"x": 0, "y": 0}
        }
    }
    return await _request("POST", f"/process-groups/{parent_id}/process-groups", json=payload)


async def create_processor_entity(group_id: str, name: str, processor_type: str, config: dict[str, Any]) -> Any:
    payload = {
        "revision": {"version": 0, "clientId": CLIENT_ID},
        "component": {
            "name": name,
            "type": processor_type,
            "position": {"x": 0, "y": 0},
            "config": config
        }
    }
    return await _request("POST", f"/process-groups/{group_id}/processors", json=payload)


async def create_connection(group_id: str, source_id: str, destination_id: str, relationships: list[str]) -> Any:
    payload = {
        "revision": {"version": 0, "clientId": CLIENT_ID},
        "component": {
            "source": {"id": source_id, "type": "PROCESSOR", "groupId": group_id},
            "destination": {"id": destination_id, "type": "PROCESSOR", "groupId": group_id},
            "selectedRelationships": relationships
        }
    }
    return await _request("POST", f"/process-groups/{group_id}/connections", json=payload)


async def get_controller_services() -> Any:
    """Fetch all available Controller Services at the global level."""
    return await _request("GET", "/flow/controller/controller-services")


async def find_controller_service_by_type(service_type: str) -> str | None:
    """Search for a controller service of a specific type and return its ID."""
    try:
        data = await get_controller_services()
        for svc in data.get("controllerServices", []):
            comp = svc.get("component", {})
            if service_type in comp.get("type", ""):
                return comp.get("id")
    except Exception:
        pass
    return None


async def update_processor_config(processor_id: str, properties: dict[str, Any]) -> Any:
    revision = await _get_revision(processor_id)
    payload = {
        "revision": revision,
        "component": {
            "id": processor_id,
            "config": {
                "properties": properties
            }
        }
    }
    return await _request("PUT", f"/processors/{processor_id}", json=payload)


async def find_processor_in_group_by_name(group_id: str, processor_name: str) -> Optional[dict[str, Any]]:
    """Search for a processor by name within a specific Process Group."""
    data = await _request("GET", f"/process-groups/{group_id}/processors")
    for proc in data.get("processors", []):
        if proc.get("component", {}).get("name") == processor_name:
            return proc
    return None


async def find_processors_by_criteria(
    group_id: str,
    name: str,
    after_processor: Optional[str] = None,
    before_processor: Optional[str] = None,
    relationship: Optional[str] = None,
    property_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Finds processors matching specific criteria:
    - Name (required)
    - Source processor (after_processor)
    - Destination processor (before_processor)
    - Connection relationship
    - Specific property values
    """
    # 1. Fetch all processors and connections in the group
    processors_data = await _request("GET", f"/process-groups/{group_id}/processors")
    all_procs = processors_data.get("processors", [])
    
    # 2. Initial filter by name
    candidates = [p for p in all_procs if p.get("component", {}).get("name") == name]
    
    if not candidates:
        return []

    # 3. Filter by connections if needed
    if after_processor or before_processor or relationship:
        connections_data = await get_connections(group_id)
        all_conns = connections_data.get("connections", [])
        
        def find_ids_by_name(p_name):
            return [p["id"] for p in all_procs if p.get("component", {}).get("name") == p_name]
            
        if after_processor:
            src_ids = find_ids_by_name(after_processor)
            new_candidates = []
            for p in candidates:
                for c in all_conns:
                    comp = c.get("component", {})
                    # Check connection FROM source TO this processor
                    if comp.get("source", {}).get("id") in src_ids and comp.get("destination", {}).get("id") == p["id"]:
                        # If relationship also specified, check it
                        if relationship:
                            if relationship in comp.get("selectedRelationships", []):
                                new_candidates.append(p)
                                break
                        else:
                            new_candidates.append(p)
                            break
            candidates = new_candidates

        if before_processor:
            dest_ids = find_ids_by_name(before_processor)
            new_candidates = []
            for p in candidates:
                for c in all_conns:
                    comp = c.get("component", {})
                    # Check connection FROM this processor TO destination
                    if comp.get("source", {}).get("id") == p["id"] and comp.get("destination", {}).get("id") in dest_ids:
                        # If relationship also specified, check it
                        if relationship:
                            if relationship in comp.get("selectedRelationships", []):
                                new_candidates.append(p)
                                break
                        else:
                            new_candidates.append(p)
                            break
            candidates = new_candidates

    # 4. Filter by property values
    if property_filters:
        new_candidates = []
        for p in candidates:
            p_props = p.get("component", {}).get("config", {}).get("properties", {})
            match = True
            for k, v in property_filters.items():
                if p_props.get(k) != v:
                    match = False
                    break
            if match:
                new_candidates.append(p)
        candidates = new_candidates
        
    return candidates


async def apply_intent_to_nifi(group_id: str, intent: dict[str, Any]) -> Any:
    """
    Apply a structured intent (processorName, property, value) directly to NiFi.
    Fulfills the 'Backend Applies Change' step of the scalability strategy.
    """
    processor_name = intent.get("processorName")
    prop = intent.get("property")
    val = intent.get("value")

    if not all([processor_name, prop, val]):
        raise ValueError("Intent missing required fields: processorName, property, or value")

    processor = await find_processor_in_group_by_name(group_id, processor_name)
    if not processor:
        raise ValueError(f"Processor '{processor_name}' not found in group {group_id}")

    return await update_processor_config(processor["id"], {prop: val})

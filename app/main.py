from typing import Any, Optional

from fastapi import FastAPI, HTTPException

from .config import settings
from .nifi_client import (
    get_all_processors,
    get_processor,
    start_processor,
    stop_processor,
)

app = FastAPI(title="Apache NiFi AI Agent")


@app.on_event("startup")
async def ensure_connection():
    try:
        await get_all_processors()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"NiFi unreachable: {exc}")


@app.get("/processors")
async def list_processors(group_id: str = "root", group_name: Optional[str] = None):
    from .nifi_client import _request, find_group_by_name

    if group_name:
        group = await find_group_by_name(group_name)
        if not group:
            raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")
        group_id = group["id"]

    if group_id == "root":
        return await get_all_processors()
    return await _request("GET", f"/process-groups/{group_id}/processors")


@app.get("/processors/login-flow")
async def fetch_login_flow():
    from .nifi_client import find_group_by_name, _request
    group = await find_group_by_name("NiFi_Flow login flow")
    if not group:
        raise HTTPException(status_code=404, detail="Login flow group not found")
    return await _request("GET", f"/process-groups/{group['id']}/processors")


@app.get("/processors/{processor_id}")
async def fetch_processor(processor_id: str):
    return await get_processor(processor_id)


@app.post("/processors/{processor_id}/start")
async def start(processor_id: str):
    return await start_processor(processor_id)


@app.post("/processors/{processor_id}/stop")
async def stop(processor_id: str):
    return await stop_processor(processor_id)


@app.get("/health")
async def health_check():
    return {"status": "ok", "nifi": str(settings.nifi_url)}

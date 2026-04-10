from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.auth.routes import get_current_user
import uuid
import secrets

router = APIRouter(prefix="/api/relay", tags=["relay"])

CURRENT_AGENT_VERSION = "0.1.0"

# --- Schemas ---
class RelayRegisterRequest(BaseModel):
    name: str
    arch: str  # arm, x86_64, mips
    site_lat: Optional[float] = None
    site_lng: Optional[float] = None

class RelayHealthRequest(BaseModel):
    agent_id: str
    cameras: list = []
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None

# --- Routes ---
@router.post("/register")
def register_relay(req: RelayRegisterRequest, current_user: dict = Depends(get_current_user)):
    db = get_db()
    tenant_id = current_user["sub"]

    if req.arch not in ["arm", "x86_64", "mips"]:
        raise HTTPException(status_code=400, detail="Invalid arch. Use: arm, x86_64, mips")

    agent_id = str(uuid.uuid4())
    auth_token = secrets.token_hex(32)

    db.table("relay_agents").insert({
        "id": agent_id,
        "tenant_id": tenant_id,
        "name": req.name,
        "auth_token": auth_token,
        "arch": req.arch,
        "version": "0.0.0",
        "site_lat": req.site_lat,
        "site_lng": req.site_lng,
        "online": False
    }).execute()

    return {
        "agent_id": agent_id,
        "auth_token": auth_token,
        "message": "Relay agent registered successfully"
    }

@router.post("/health")
def relay_health(req: RelayHealthRequest, x_agent_token: str = Header(...)):
    db = get_db()

    # Verify agent token
    agent = db.table("relay_agents").select("*").eq("id", req.agent_id).eq("auth_token", x_agent_token).execute()
    if not agent.data:
        raise HTTPException(status_code=401, detail="Invalid agent token")

    # Update agent status
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    db.table("relay_agents").update({
        "online": True,
        "last_seen": now
    }).eq("id", req.agent_id).execute()

    # Update each camera status
    for cam in req.cameras:
        cam_id = cam.get("camera_id")
        if cam_id:
            db.table("cameras").update({
                "online": cam.get("online", False),
                "fps": cam.get("fps"),
                "bitrate": cam.get("bitrate"),
                "last_seen": now
            }).eq("id", cam_id).execute()

            # Log health snapshot
            db.table("camera_health_log").insert({
                "camera_id": cam_id,
                "fps": cam.get("fps"),
                "bitrate": cam.get("bitrate"),
                "online": cam.get("online", False),
                "relay_latency_ms": cam.get("latency_ms"),
                "decode_errors": cam.get("decode_errors", 0)
            }).execute()

    return {"status": "ok", "version": CURRENT_AGENT_VERSION}

@router.get("/version")
def get_version():
    return {
        "version": CURRENT_AGENT_VERSION,
        "download_url": f"https://neuralwatch.live/agent/neuralwatch-agent-{CURRENT_AGENT_VERSION}"
    }

@router.get("")
def list_relays(current_user: dict = Depends(get_current_user)):
    db = get_db()
    result = db.table("relay_agents").select("*").eq("tenant_id", current_user["sub"]).execute()
    return result.data

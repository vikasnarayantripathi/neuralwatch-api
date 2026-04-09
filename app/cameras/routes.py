from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.auth.routes import get_current_user
from app.database import get_db
import uuid

router = APIRouter(prefix="/api/cameras", tags=["cameras"])

# --- Schemas ---
class CameraCreate(BaseModel):
    name: str
    rtsp_url: str
    brand: Optional[str] = "generic"
    relay_agent_id: Optional[str] = None

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    brand: Optional[str] = None
    zone_config: Optional[dict] = None
    alert_config: Optional[dict] = None

# --- Routes ---
@router.get("")
def list_cameras(current_user: dict = Depends(get_current_user)):
    db = get_db()
    result = db.table("cameras").select("*").eq("tenant_id", current_user["sub"]).execute()
    return result.data

@router.post("")
def add_camera(req: CameraCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    tenant_id = current_user["sub"]

    # Check camera quota
    tenant = db.table("tenants").select("camera_quota, plan").eq("id", tenant_id).execute()
    if not tenant.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    quota = tenant.data[0]["camera_quota"]
    current_count = db.table("cameras").select("id").eq("tenant_id", tenant_id).execute()

    if len(current_count.data) >= quota:
        raise HTTPException(status_code=400, detail=f"Camera quota reached. Your plan allows {quota} camera(s).")

    camera_id = str(uuid.uuid4())
    db.table("cameras").insert({
        "id": camera_id,
        "tenant_id": tenant_id,
        "name": req.name,
        "rtsp_url": req.rtsp_url,
        "brand": req.brand,
        "relay_agent_id": req.relay_agent_id,
        "online": False
    }).execute()

    return {"message": "Camera added successfully", "camera_id": camera_id}

@router.get("/{camera_id}")
def get_camera(camera_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    result = db.table("cameras").select("*").eq("id", camera_id).eq("tenant_id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    return result.data[0]

@router.put("/{camera_id}")
def update_camera(camera_id: str, req: CameraUpdate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")
    db.table("cameras").update(update_data).eq("id", camera_id).eq("tenant_id", current_user["sub"]).execute()
    return {"message": "Camera updated successfully"}

@router.delete("/{camera_id}")
def delete_camera(camera_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    db.table("cameras").delete().eq("id", camera_id).eq("tenant_id", current_user["sub"]).execute()
    return {"message": "Camera deleted successfully"}

@router.get("/{camera_id}/health")
def camera_health(camera_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    result = db.table("cameras").select("online, last_seen, health_score, fps, bitrate, resolution").eq("id", camera_id).eq("tenant_id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    return result.data[0]

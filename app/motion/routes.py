from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.auth.routes import get_current_user
from app.database import get_db
from datetime import datetime, timezone
import uuid

router = APIRouter(tags=["motion"])

# --- Schemas ---
class MotionEventCreate(BaseModel):
    camera_id: str
    score: float
    thumbnail_url: Optional[str] = None
    zone_id: Optional[str] = None

class AlertAction(BaseModel):
    feedback: Optional[str] = None

# --- Motion Events ---
@router.get("/api/cameras/{camera_id}/motion")
def list_motion_events(
    camera_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()

    # Verify camera belongs to tenant
    cam = db.table("cameras").select("id").eq("id", camera_id).eq("tenant_id", current_user["sub"]).execute()
    if not cam.data:
        raise HTTPException(status_code=404, detail="Camera not found")

    result = db.table("motion_events").select("*").eq("camera_id", camera_id).order("ts", desc=True).limit(limit).execute()
    return result.data

# --- Internal: called by relay agent to report motion ---
@router.post("/api/internal/motion")
def report_motion(req: MotionEventCreate, x_agent_token: str = Header(...)):
    db = get_db()

    # Verify agent token
    agent = db.table("relay_agents").select("*").eq("auth_token", x_agent_token).execute()
    if not agent.data:
        raise HTTPException(status_code=401, detail="Invalid agent token")

    # Verify camera belongs to this agent's tenant
    cam = db.table("cameras").select("*").eq("id", req.camera_id).execute()
    if not cam.data:
        raise HTTPException(status_code=404, detail="Camera not found")

    camera = cam.data[0]

    if not (0.0 <= req.score <= 1.0):
        raise HTTPException(status_code=400, detail="Score must be between 0.0 and 1.0")

    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Insert motion event
    db.table("motion_events").insert({
        "id": event_id,
        "camera_id": req.camera_id,
        "ts": now,
        "score": req.score,
        "thumbnail_url": req.thumbnail_url,
        "zone_id": req.zone_id,
        "alert_sent": False,
        "dismissed": False,
        "confirmed": False
    }).execute()

    # Check alert config
    alert_config = camera.get("alert_config", {})
    threshold = alert_config.get("motion_threshold", 0.3)
    alerts_enabled = alert_config.get("enabled", True)

    alert_id = None
    if alerts_enabled and req.score >= threshold:
        alert_id = str(uuid.uuid4())
        db.table("alerts").insert({
            "id": alert_id,
            "tenant_id": camera["tenant_id"],
            "camera_id": req.camera_id,
            "type": "motion",
            "channel": "email",
            "payload": {
                "event_id": event_id,
                "score": req.score,
                "thumbnail_url": req.thumbnail_url,
                "camera_name": camera.get("name")
            },
            "delivered": False
        }).execute()

        # Mark alert sent
        db.table("motion_events").update({
            "alert_sent": True
        }).eq("id", event_id).execute()

    # Log to user_actions
    db.table("user_actions").insert({
        "tenant_id": camera["tenant_id"],
        "user_id": camera["tenant_id"],
        "action": "motion_detected",
        "metadata": {
            "camera_id": req.camera_id,
            "score": req.score,
            "event_id": event_id
        }
    }).execute()

    return {
        "event_id": event_id,
        "alert_created": alert_id is not None,
        "alert_id": alert_id
    }

# --- Alert actions ---
@router.post("/api/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()

    alert = db.table("alerts").select("*").eq("id", alert_id).eq("tenant_id", current_user["sub"]).execute()
    if not alert.data:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.table("alerts").update({
        "read_at": datetime.now(timezone.utc).isoformat(),
        "false_positive": True
    }).eq("id", alert_id).execute()

    # Log to feedback_loop
    db.table("feedback_loop").insert({
        "alert_id": alert_id,
        "user_id": current_user["sub"],
        "action": "dismissed",
        "used_for_training": False
    }).execute()

    return {"message": "Alert dismissed"}

@router.post("/api/alerts/{alert_id}/confirm")
def confirm_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()

    alert = db.table("alerts").select("*").eq("id", alert_id).eq("tenant_id", current_user["sub"]).execute()
    if not alert.data:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.table("alerts").update({
        "read_at": datetime.now(timezone.utc).isoformat(),
        "false_positive": False
    }).eq("id", alert_id).execute()

    # Log to feedback_loop
    db.table("feedback_loop").insert({
        "alert_id": alert_id,
        "user_id": current_user["sub"],
        "action": "confirmed",
        "used_for_training": False
    }).execute()

    return {"message": "Alert confirmed"}

@router.get("/api/alerts")
def list_alerts(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    result = db.table("alerts").select("*").eq("tenant_id", current_user["sub"]).order("created_at", desc=True).limit(limit).execute()
    return result.data

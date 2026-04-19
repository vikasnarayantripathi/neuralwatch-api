from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.auth.routes import router as auth_router
from app.cameras.routes import router as cameras_router
from app.playback import router as playback_router
from app.motion.routes import router as motion_router
from app.relay.routes import router as relay_router
from app.ingest import start_camera_stream, stop_camera_stream, get_active_streams
from app.auth.utils import get_current_tenant
from app.database import get_db
import uvicorn
import asyncio

app = FastAPI(
    title="NeuralWatch API",
    description="Universal Cloud Camera Recording Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(cameras_router)
app.include_router(playback_router)
app.include_router(motion_router)
app.include_router(relay_router)


# ── Core endpoints ─────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "NeuralWatch API is running",
        "version": "2.0.0"
    }

@app.get("/health")
def health():
    active = get_active_streams()
    return {
        "status": "healthy",
        "active_streams": len(active),
        "stream_ids": active
    }


# ── Stream control endpoints ───────────────────────────────
@app.post("/api/stream/{camera_id}/start")
async def start_stream(
    camera_id: str,
    tenant=Depends(get_current_tenant)
):
    db = get_db()
    cam = db.table("cameras").select("*").eq(
        "id", camera_id
    ).eq("tenant_id", tenant["id"]).execute()
    if not cam.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera = cam.data[0]
    rtsp_url = camera.get("rtsp_url") or camera.get("stream_url")
    if not rtsp_url:
        raise HTTPException(status_code=400, detail="Camera has no stream URL")
    await start_camera_stream(
        camera_id=camera_id,
        rtsp_url=rtsp_url,
        tenant_id=tenant["id"]
    )
    return {"status": "started", "camera_id": camera_id}


@app.post("/api/stream/{camera_id}/stop")
async def stop_stream(
    camera_id: str,
    tenant=Depends(get_current_tenant)
):
    db = get_db()
    cam = db.table("cameras").select("*").eq(
        "id", camera_id
    ).eq("tenant_id", tenant["id"]).execute()
    if not cam.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    await stop_camera_stream(camera_id)
    return {"status": "stopped", "camera_id": camera_id}


@app.get("/api/stream/active")
async def list_active_streams(
    tenant=Depends(get_current_tenant)
):
    active = get_active_streams()
    return {
        "active_streams": len(active),
        "camera_ids": active
    }


# ── Startup: auto-resume streams ───────────────────────────
@app.on_event("startup")
async def auto_resume_streams():
    await asyncio.sleep(3)
    db = get_db()
    try:
        result = db.table("cameras").select("*").eq(
            "recording_enabled", True
        ).execute()
        cameras = result.data or []
        print(f"[STARTUP] Auto-resuming {len(cameras)} camera streams")
        for camera in cameras:
            rtsp_url = camera.get("rtsp_url") or camera.get("stream_url")
            if rtsp_url:
                await start_camera_stream(
                    camera_id=camera["id"],
                    rtsp_url=rtsp_url,
                    tenant_id=camera["tenant_id"]
                )
    except Exception as e:
        print(f"[STARTUP] Auto-resume error: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

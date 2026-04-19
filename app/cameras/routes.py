# ── New endpoints: RTSP/RTMP/QR wizard + MediaMTX ──────────────────────────

import os
import secrets
from datetime import datetime, timezone
from app.mediamtx import MediaMTXClient
from app.crypto import encrypt, decrypt, build_rtsp_url, mask_rtsp_url
from app.probe import probe_rtsp

MEDIAMTX_URL = os.environ.get("MEDIAMTX_URL", "")
mtx = MediaMTXClient(MEDIAMTX_URL) if MEDIAMTX_URL else None


# ── Schemas ──────────────────────────────────────────────────────────────────

class RTSPCameraInput(BaseModel):
    name: str
    camera_brand: str = "generic"
    local_ip: str
    rtsp_port: int = 554
    rtsp_path: str = "/stream1"
    cam_username: str = "admin"
    cam_password: str
    room_id: Optional[str] = None
    has_ptz: bool = False


class RTMPCameraInput(BaseModel):
    name: str
    camera_brand: str = "generic"
    room_id: Optional[str] = None
    has_ptz: bool = False
    has_audio: bool = False


class QRCameraInput(BaseModel):
    name: str
    wifi_ssid: str
    wifi_password: str
    room_id: Optional[str] = None


class TestConnectionInput(BaseModel):
    local_ip: str
    rtsp_port: int = 554
    rtsp_path: str = "/stream1"
    cam_username: str = "admin"
    cam_password: str
    camera_brand: str = "generic"


# ── Test connection ───────────────────────────────────────────────────────────

@router.post("/test-connection")
async def test_connection(
    body: TestConnectionInput,
    current_user: dict = Depends(get_current_user)
):
    rtsp_url = build_rtsp_url(
        body.local_ip, body.rtsp_port,
        body.cam_username, body.cam_password,
        body.rtsp_path
    )
    result = await probe_rtsp(rtsp_url)
    is_private = _is_private_ip(body.local_ip)
    return {
        "ok": result.ok,
        "resolution": f"{result.width}x{result.height}" if result.width else None,
        "codec": result.codec,
        "fps": result.fps,
        "has_audio": result.has_audio,
        "latency_ms": result.latency_ms,
        "error": result.error,
        "is_private_network": is_private,
        "rtmp_recommended": is_private
    }


# ── Add RTSP camera ───────────────────────────────────────────────────────────

@router.post("/add-rtsp")
async def add_rtsp_camera(
    body: RTSPCameraInput,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    tenant_id = current_user["sub"]

    rtsp_url = build_rtsp_url(
        body.local_ip, body.rtsp_port,
        body.cam_username, body.cam_password,
        body.rtsp_path
    )

    cam_id      = str(uuid.uuid4())
    stream_path = f"cam_{cam_id.replace('-','')[:16]}"
    hls_url     = mtx.hls_url(stream_path) if mtx else ""
    webrtc_url  = mtx.webrtc_url(stream_path) if mtx else ""

    db.table("cameras").insert({
        "id":                 cam_id,
        "tenant_id":          tenant_id,
        "name":               body.name,
        "connection_method":  "rtsp_pull",
        "camera_brand":       body.camera_brand,
        "local_ip":           body.local_ip,
        "rtsp_port":          body.rtsp_port,
        "rtsp_path":          body.rtsp_path,
        "cam_username":       body.cam_username,
        "cam_password_enc":   encrypt(body.cam_password),
        "rtsp_url_encrypted": encrypt(rtsp_url),
        "stream_path":        stream_path,
        "hls_url":            hls_url,
        "webrtc_url":         webrtc_url,
        "room_id":            body.room_id,
        "has_ptz":            body.has_ptz,
        "connection_status":  "connecting",
        "is_active":          True,
    }).execute()

    # Register path in MediaMTX
    if mtx:
        await mtx.add_path(
            path_name=stream_path,
            source_url=rtsp_url,
            source_on_demand=True
        )

    return {
        "ok": True,
        "camera_id": cam_id,
        "stream_path": stream_path,
        "hls_url": hls_url,
        "webrtc_url": webrtc_url,
        "is_private_network": _is_private_ip(body.local_ip),
        "rtmp_recommended": _is_private_ip(body.local_ip),
        "message": "Camera added. Stream connecting..."
    }


# ── Add RTMP camera ───────────────────────────────────────────────────────────

@router.post("/add-rtmp")
async def add_rtmp_camera(
    body: RTMPCameraInput,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    tenant_id = current_user["sub"]

    cam_id      = str(uuid.uuid4())
    push_key    = secrets.token_urlsafe(24)
    stream_path = f"cam_{cam_id.replace('-','')[:16]}"
    hls_url     = mtx.hls_url(stream_path) if mtx else ""
    webrtc_url  = mtx.webrtc_url(stream_path) if mtx else ""
    rtmp_url    = mtx.rtmp_push_url(stream_path) if mtx else ""
    rtmps_url   = mtx.rtmps_push_url(stream_path) if mtx else ""

    db.table("cameras").insert({
        "id":                cam_id,
        "tenant_id":         tenant_id,
        "name":              body.name,
        "connection_method": "rtmp_push",
        "camera_brand":      body.camera_brand,
        "rtmp_push_key":     push_key,
        "rtmp_ingest_url":   rtmp_url,
        "stream_path":       stream_path,
        "hls_url":           hls_url,
        "webrtc_url":        webrtc_url,
        "room_id":           body.room_id,
        "has_ptz":           body.has_ptz,
        "has_audio":         body.has_audio,
        "connection_status": "provisioning",
        "is_active":         True,
    }).execute()

    # Register push path in MediaMTX (no source = camera pushes)
    if mtx:
        await mtx.add_path(
            path_name=stream_path,
            source_url=None,
            source_on_demand=False
        )

    return {
        "ok": True,
        "camera_id": cam_id,
        "stream_path": stream_path,
        "hls_url": hls_url,
        "webrtc_url": webrtc_url,
        "rtmp_push_url": rtmp_url,
        "rtmps_push_url": rtmps_url,
        "push_key": push_key,
        "message": "Camera slot created. Configure your camera to push to the RTMP URL."
    }


# ── Add QR camera ─────────────────────────────────────────────────────────────

@router.post("/add-qr")
async def add_qr_camera(
    body: QRCameraInput,
    current_user: dict = Depends(get_current_user)
):
    import json, base64
    db = get_db()
    tenant_id = current_user["sub"]

    cam_id      = str(uuid.uuid4())
    token       = str(uuid.uuid4())
    stream_path = f"cam_{cam_id.replace('-','')[:16]}"
    push_key    = secrets.token_urlsafe(24)
    rtmps_url   = mtx.rtmps_push_url(stream_path) if mtx else ""
    rtmp_url    = mtx.rtmp_push_url(stream_path) if mtx else ""

    qr_data = {
        "v": 1,
        "ssid": body.wifi_ssid,
        "pass": body.wifi_password,
        "push": rtmps_url,
        "token": token,
        "tenant": tenant_id
    }
    qr_payload = base64.b64encode(
        json.dumps(qr_data).encode()
    ).decode()

    db.table("cameras").insert({
        "id":                cam_id,
        "tenant_id":         tenant_id,
        "name":              body.name,
        "connection_method": "qr_provision",
        "rtmp_push_key":     push_key,
        "rtmp_ingest_url":   rtmp_url,
        "stream_path":       stream_path,
        "hls_url":           mtx.hls_url(stream_path) if mtx else "",
        "webrtc_url":        mtx.webrtc_url(stream_path) if mtx else "",
        "room_id":           body.room_id,
        "provisioning_token": token,
        "provisioning_qr":   qr_payload,
        "wifi_ssid_enc":     encrypt(body.wifi_ssid),
        "wifi_pass_enc":     encrypt(body.wifi_password),
        "connection_status": "provisioning",
        "is_active":         True,
    }).execute()

    if mtx:
        await mtx.add_path(
            path_name=stream_path,
            source_url=None,
            source_on_demand=False
        )

    return {
        "ok": True,
        "camera_id": cam_id,
        "qr_payload": qr_payload,
        "provisioning_token": token,
        "hls_url": mtx.hls_url(stream_path) if mtx else "",
        "message": "Scan the QR code with your camera to connect"
    }


# ── Camera stream status ──────────────────────────────────────────────────────

@router.get("/{camera_id}/status")
async def camera_stream_status(
    camera_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    result = db.table("cameras").select("*").eq(
        "id", camera_id
    ).eq("tenant_id", current_user["sub"]).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Camera not found")

    camera = result.data[0]
    stream_path = camera.get("stream_path")

    is_active = False
    if mtx and stream_path:
        is_active = await mtx.is_path_active(stream_path)

    new_status = "online" if is_active else "offline"

    if camera.get("connection_status") != new_status:
        db.table("cameras").update({
            "connection_status": new_status
        }).eq("id", camera_id).execute()

    return {
        "camera_id": camera_id,
        "status": new_status,
        "is_streaming": is_active,
        "hls_url": camera.get("hls_url"),
        "webrtc_url": camera.get("webrtc_url"),
    }


# ── Get stream URLs ───────────────────────────────────────────────────────────

@router.get("/{camera_id}/stream")
async def get_stream_url(
    camera_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    result = db.table("cameras").select(
        "id, name, hls_url, webrtc_url, connection_method, connection_status"
    ).eq("id", camera_id).eq("tenant_id", current_user["sub"]).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Camera not found")

    return result.data[0]


# ── Get RTMP push config ──────────────────────────────────────────────────────

@router.get("/{camera_id}/push-config")
async def get_push_config(
    camera_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    result = db.table("cameras").select("*").eq(
        "id", camera_id
    ).eq("tenant_id", current_user["sub"]).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Camera not found")

    camera = result.data[0]
    stream_path = camera.get("stream_path", "")

    return {
        "rtmp_url":  mtx.rtmp_push_url(stream_path) if mtx else "",
        "rtmps_url": mtx.rtmps_push_url(stream_path) if mtx else "",
        "stream_key": camera.get("rtmp_push_key", ""),
    }


# ── Brand templates ───────────────────────────────────────────────────────────

@router.get("/brands/templates")
async def get_brand_templates(
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    result = db.table("camera_brand_templates").select("*").order("display_name").execute()
    return result.data


# ── Helper ────────────────────────────────────────────────────────────────────

def _is_private_ip(ip: str) -> bool:
    import ipaddress
    try:
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return False

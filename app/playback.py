from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from app.auth.utils import get_current_tenant
from app.storage import get_presigned_url, list_segments
from app.database import get_db
from datetime import datetime, timezone

router = APIRouter(prefix="/api/playback", tags=["playback"])

@router.get("/{camera_id}/segments")
async def get_segments(
    camera_id: str,
    date: str = None,
    tenant=Depends(get_current_tenant)
):
    db = get_db()
    cam = db.table("cameras").select("*").eq(
        "id", camera_id
    ).eq("tenant_id", tenant["id"]).execute()
    if not cam.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    query = db.table("recording_segments").select("*").eq(
        "camera_id", camera_id
    ).order("segment_index", desc=False)
    if date:
        query = query.like("r2_key", f"%/{date}/%")
    result = query.execute()
    segments = result.data or []
    segments_with_urls = []
    for seg in segments:
        url = get_presigned_url(seg["r2_key"], expires_in=3600)
        segments_with_urls.append({
            "id": seg["id"],
            "segment_index": seg["segment_index"],
            "started_at": seg["started_at"],
            "duration_seconds": seg["duration_seconds"],
            "size_bytes": seg["size_bytes"],
            "url": url
        })
    return {
        "camera_id": camera_id,
        "date": date,
        "total": len(segments_with_urls),
        "segments": segments_with_urls
    }

@router.get("/{camera_id}/playlist")
async def get_playlist(
    camera_id: str,
    date: str = None,
    tenant=Depends(get_current_tenant)
):
    db = get_db()
    cam = db.table("cameras").select("*").eq(
        "id", camera_id
    ).eq("tenant_id", tenant["id"]).execute()
    if not cam.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = db.table("recording_segments").select("*").eq(
        "camera_id", camera_id
    ).like("r2_key", f"%/{date}/%").order(
        "segment_index", desc=False
    ).execute()
    segments = result.data or []
    if not segments:
        raise HTTPException(
            status_code=404,
            detail=f"No recordings found for {date}"
        )
    playlist_lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:10",
        "#EXT-X-MEDIA-SEQUENCE:0",
    ]
    for seg in segments:
        url = get_presigned_url(seg["r2_key"], expires_in=3600)
        playlist_lines.append(f"#EXTINF:{seg['duration_seconds']:.1f},")
        playlist_lines.append(url)
    playlist_lines.append("#EXT-X-ENDLIST")
    return PlainTextResponse(
        content="\n".join(playlist_lines),
        media_type="application/vnd.apple.mpegurl"
    )

@router.get("/{camera_id}/dates")
async def get_recording_dates(
    camera_id: str,
    tenant=Depends(get_current_tenant)
):
    db = get_db()
    cam = db.table("cameras").select("*").eq(
        "id", camera_id
    ).eq("tenant_id", tenant["id"]).execute()
    if not cam.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    prefix = f"cameras/{camera_id}/"
    keys = list_segments(prefix)
    dates = set()
    for key in keys:
        parts = key.split("/")
        if len(parts) >= 3:
            dates.add(parts[2])
    return {
        "camera_id": camera_id,
        "dates": sorted(list(dates), reverse=True)
    }

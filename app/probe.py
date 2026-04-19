# app/probe.py
import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

FFPROBE_TIMEOUT = 8


@dataclass
class ProbeResult:
    ok: bool
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None
    fps: Optional[float] = None
    has_audio: bool = False
    error: Optional[str] = None
    latency_ms: Optional[int] = None


async def probe_rtsp(rtsp_url: str) -> ProbeResult:
    """Test an RTSP stream using ffprobe. Falls back to TCP check if ffprobe missing."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-rtsp_transport", "tcp",
        "-timeout", str(FFPROBE_TIMEOUT * 1_000_000),
        rtsp_url
    ]

    start = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=FFPROBE_TIMEOUT + 2
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode != 0:
            return _parse_error(stderr.decode().strip(), elapsed_ms)

        data = json.loads(stdout.decode())
        return _parse_streams(data.get("streams", []), elapsed_ms)

    except asyncio.TimeoutError:
        return ProbeResult(
            ok=False,
            error="Timed out — camera unreachable or wrong IP"
        )
    except FileNotFoundError:
        # ffprobe not installed — fall back to TCP socket check
        logger.warning("ffprobe not found, using TCP fallback")
        return await _tcp_probe(rtsp_url)
    except Exception as e:
        return ProbeResult(ok=False, error=f"Probe failed: {str(e)}")


def _parse_streams(streams: list, elapsed_ms: int) -> ProbeResult:
    if not streams:
        return ProbeResult(
            ok=False,
            error="Connected but no streams found — try a different RTSP path"
        )

    result = ProbeResult(ok=True, latency_ms=elapsed_ms)

    for s in streams:
        if s.get("codec_type") == "video":
            result.width  = s.get("width")
            result.height = s.get("height")
            result.codec  = s.get("codec_name", "").upper()
            fps_str = s.get("avg_frame_rate", "0/1")
            try:
                num, den = fps_str.split("/")
                result.fps = round(int(num) / int(den), 1) if int(den) > 0 else None
            except Exception:
                result.fps = None
        elif s.get("codec_type") == "audio":
            result.has_audio = True

    return result


def _parse_error(stderr: str, elapsed_ms: int) -> ProbeResult:
    err = stderr.lower()
    if "401" in err or "unauthorized" in err:
        return ProbeResult(ok=False, error="Wrong username or password")
    if "connection refused" in err:
        return ProbeResult(ok=False, error="Connection refused — check IP and port")
    if "no route to host" in err or "network unreachable" in err:
        return ProbeResult(
            ok=False,
            error="Camera not reachable from cloud — it's on your local network. "
                  "Use RTMP Push mode instead."
        )
    if "timeout" in err:
        return ProbeResult(ok=False, error="Timed out — camera offline or wrong IP")
    if "invalid data" in err:
        return ProbeResult(
            ok=False,
            error="Connected but couldn't read stream — try a different RTSP path"
        )
    return ProbeResult(ok=False, error=f"Connection failed: {stderr[:200]}")


async def _tcp_probe(rtsp_url: str) -> ProbeResult:
    """Fallback: just check if TCP port is reachable."""
    import re
    match = re.search(r"@([^:/]+):?(\d+)?/", rtsp_url)
    if not match:
        return ProbeResult(ok=False, error="Could not parse RTSP URL")

    host = match.group(1)
    port = int(match.group(2) or 554)

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0
        )
        writer.close()
        await writer.wait_closed()
        return ProbeResult(
            ok=True,
            codec="UNKNOWN",
            error=None
        )
    except asyncio.TimeoutError:
        return ProbeResult(
            ok=False,
            error="Port unreachable — camera offline or on private network"
        )
    except ConnectionRefusedError:
        return ProbeResult(
            ok=False,
            error="Port refused — check if RTSP is enabled on camera"
        )
    except Exception as e:
        return ProbeResult(ok=False, error=str(e))

# app/mediamtx.py
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MediaMTXClient:
    def __init__(self, base_url: str, api_user: str = "", api_pass: str = ""):
        self.base = base_url.rstrip("/")
        self.auth = (api_user, api_pass) if api_user else None
        self._client = httpx.AsyncClient(timeout=10.0)

    async def add_path(
        self,
        path_name: str,
        source_url: Optional[str] = None,
        source_on_demand: bool = True,
        record: bool = False,
    ) -> dict:
        payload = {"sourceOnDemand": source_on_demand, "record": record}
        if source_url:
            payload["source"] = source_url

        url = f"{self.base}/v3/config/paths/add/{path_name}"
        logger.info(f"MediaMTX: registering path '{path_name}'")

        try:
            resp = await self._client.post(url, json=payload, auth=self.auth)
            if resp.status_code in (200, 201):
                return {"ok": True, "path": path_name}
            if resp.status_code == 409:
                return await self.update_path(path_name, source_url, source_on_demand)
            return {"ok": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.error(f"MediaMTX add_path error: {e}")
            return {"ok": False, "error": str(e)}

    async def update_path(
        self,
        path_name: str,
        source_url: Optional[str] = None,
        source_on_demand: bool = True,
    ) -> dict:
        payload = {"sourceOnDemand": source_on_demand}
        if source_url:
            payload["source"] = source_url
        url = f"{self.base}/v3/config/paths/patch/{path_name}"
        try:
            resp = await self._client.patch(url, json=payload, auth=self.auth)
            return {"ok": True, "path": path_name, "action": "updated"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def remove_path(self, path_name: str) -> dict:
        url = f"{self.base}/v3/config/paths/delete/{path_name}"
        try:
            resp = await self._client.delete(url, auth=self.auth)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def is_path_active(self, path_name: str) -> bool:
        try:
            url = f"{self.base}/v3/paths/list"
            resp = await self._client.get(url, auth=self.auth)
            paths = resp.json().get("items", [])
            for p in paths:
                if p.get("name") == path_name:
                    return p.get("ready", False)
            return False
        except Exception as e:
            logger.warning(f"MediaMTX status check failed: {e}")
            return False

    def hls_url(self, path_name: str) -> str:
        return f"{self.base}/{path_name}/index.m3u8"

    def webrtc_url(self, path_name: str) -> str:
        return f"{self.base}/{path_name}/whep"

    def rtmp_push_url(self, path_name: str) -> str:
        host = self.base.replace("https://", "").replace("http://", "")
        return f"rtmp://{host}:1935/{path_name}"

    def rtmps_push_url(self, path_name: str) -> str:
        host = self.base.replace("https://", "").replace("http://", "")
        return f"rtmps://{host}:443/{path_name}"

    async def close(self):
        await self._client.aclose()

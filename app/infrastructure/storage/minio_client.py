from __future__ import annotations

import asyncio
from http.client import HTTPResponse
from typing import cast
from urllib.request import Request, urlopen


async def check_minio_ready(endpoint: str, timeout_seconds: float = 2.0) -> bool:
    url = f"{endpoint.rstrip('/')}/minio/health/ready"

    def _probe() -> bool:
        try:
            request = Request(url, method='GET')
            with urlopen(request, timeout=timeout_seconds) as response:
                status = cast(HTTPResponse, response).status
                return 200 <= status < 300
        except Exception:
            return False

    return await asyncio.to_thread(_probe)

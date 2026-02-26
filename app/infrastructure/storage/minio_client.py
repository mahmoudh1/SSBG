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


class ObjectStorageError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], bytes] = {}

    async def put_object(self, bucket: str, object_name: str, data: bytes) -> None:
        if not bucket or not object_name:
            raise ObjectStorageError('Invalid storage target')
        self._objects[(bucket, object_name)] = data

    async def get_object(self, bucket: str, object_name: str) -> bytes | None:
        return self._objects.get((bucket, object_name))

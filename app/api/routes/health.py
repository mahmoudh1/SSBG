from fastapi import APIRouter, Depends

from app.api.dependencies import get_request_id
from app.services.health_service import get_liveness_status, get_readiness_status

router = APIRouter(prefix='/health')


def _success_payload(data: dict[str, object], request_id: str) -> dict[str, object]:
    return {'data': data, 'meta': {'request_id': request_id}}


@router.get('/live')
async def liveness(request_id: str = Depends(get_request_id)) -> dict[str, object]:
    data = await get_liveness_status()
    return _success_payload(data=data, request_id=request_id)


@router.get('/ready')
async def readiness(request_id: str = Depends(get_request_id)) -> dict[str, object]:
    data = await get_readiness_status()
    return _success_payload(data=data, request_id=request_id)

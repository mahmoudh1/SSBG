from fastapi import APIRouter

router = APIRouter()


@router.get('')
async def list_alerts() -> dict[str, str]:
    return {'message': 'Alerts admin endpoint placeholder'}

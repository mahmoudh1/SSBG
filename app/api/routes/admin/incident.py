from fastapi import APIRouter

router = APIRouter()


@router.get('')
async def get_incident_state() -> dict[str, str]:
    return {'message': 'Incident admin endpoint placeholder'}

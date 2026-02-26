from fastapi import APIRouter

router = APIRouter()


@router.post('')
async def submit_restore() -> dict[str, str]:
    return {'message': 'Restore endpoint placeholder'}

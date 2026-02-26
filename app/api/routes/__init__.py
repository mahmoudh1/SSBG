from fastapi import APIRouter, Depends

from app.api.dependencies import require_permission
from app.api.routes import audit, backups, health, restores
from app.api.routes.admin import alerts, incident, keys, policies

router = APIRouter()
router.include_router(health.router, tags=['health'])
router.include_router(
    backups.router,
    prefix='/backups',
    tags=['backups'],
    dependencies=[Depends(require_permission('backups'))],
)
router.include_router(
    restores.router,
    prefix='/restores',
    tags=['restores'],
    dependencies=[Depends(require_permission('restores'))],
)
router.include_router(
    audit.router,
    prefix='/audit',
    tags=['audit'],
    dependencies=[Depends(require_permission('audit'))],
)
router.include_router(
    alerts.router,
    prefix='/admin/alerts',
    tags=['admin-alerts'],
    dependencies=[Depends(require_permission('admin'))],
)
router.include_router(
    incident.router,
    prefix='/admin/incident',
    tags=['admin-incident'],
    dependencies=[Depends(require_permission('admin'))],
)
router.include_router(
    keys.router,
    prefix='/admin/keys',
    tags=['admin-keys'],
    dependencies=[Depends(require_permission('admin'))],
)
router.include_router(
    policies.router,
    prefix='/admin/policies',
    tags=['admin-policies'],
    dependencies=[Depends(require_permission('admin'))],
)

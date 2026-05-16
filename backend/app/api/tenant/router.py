from fastapi import APIRouter

from app.api.tenant.auth import router as auth_router
from app.api.tenant.core import router as core_router
from app.api.tenant.intelligence import router as intelligence_router
from app.api.tenant.messaging import router as messaging_router
from app.api.tenant.ops import router as ops_router
from app.api.tenant.settings import router as settings_router
from app.api.tenant.team import router as team_router
from app.core.responses import success_response

router = APIRouter()
router.include_router(auth_router)
router.include_router(core_router)
router.include_router(settings_router)
router.include_router(team_router)
router.include_router(ops_router)
router.include_router(messaging_router)
router.include_router(intelligence_router)


@router.get("/health")
async def tenant_health() -> dict:
    return success_response({"scope": "tenant"})

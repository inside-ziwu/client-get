from fastapi import APIRouter

from app.api.internal.ops import router as ops_router
from app.core.responses import success_response

router = APIRouter()
router.include_router(ops_router)


@router.get("/health")
async def internal_health() -> dict:
    return success_response({"scope": "internal"})

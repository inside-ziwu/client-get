from fastapi import APIRouter

from app.api.webhooks.engagelab import router as engagelab_router
from app.core.responses import success_response

router = APIRouter()
router.include_router(engagelab_router)


@router.get("/health")
async def webhook_health() -> dict:
    return success_response({"scope": "webhooks"})

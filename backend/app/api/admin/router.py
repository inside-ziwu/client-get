from fastapi import APIRouter

from app.api.admin.auth import router as auth_router
from app.api.admin.collection import router as collection_router
from app.api.admin.config import router as config_router
from app.api.admin.contact_classification import router as contact_classification_router
from app.api.admin.tenants import router as tenants_router
from app.core.responses import success_response

router = APIRouter()
router.include_router(auth_router)
router.include_router(config_router)
router.include_router(collection_router)
router.include_router(tenants_router)
router.include_router(contact_classification_router)


@router.get("/health")
async def admin_health() -> dict:
    return success_response({"scope": "admin"})

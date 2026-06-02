from fastapi import APIRouter, Depends

from app.core.responses import paginated_response, success_response
from app.db.pools import get_connection
from app.security.internal import ServiceAuthContext, require_service_scopes
from app.services.internal_ops_service import InternalOpsService

router = APIRouter(tags=["internal-ops"])
service = InternalOpsService()


@router.get("/collection/credentials/{source_type}")
async def list_collection_credentials(
    source_type: str,
    _: ServiceAuthContext = Depends(require_service_scopes("collection:write")),
    conn=Depends(get_connection),
) -> dict:
    items = await service.list_collection_credentials(conn, source_type)
    return paginated_response(items, total=len(items))


@router.post("/sending/due-emails/claim")
async def claim_due_emails(
    payload: dict,
    _: ServiceAuthContext = Depends(require_service_scopes("sending:claim")),
    conn=Depends(get_connection),
) -> dict:
    return success_response(await service.claim_due_emails(conn, payload))


@router.post("/sending/emails/{email_id}/mark-sent")
async def mark_email_sent(
    email_id: str,
    payload: dict,
    _: ServiceAuthContext = Depends(require_service_scopes("sending:write")),
    conn=Depends(get_connection),
) -> dict:
    return success_response(await service.mark_email_sent(conn, email_id=email_id, payload=payload))


@router.post("/sending/emails/{email_id}/mark-failed")
async def mark_email_failed(
    email_id: str,
    payload: dict,
    _: ServiceAuthContext = Depends(require_service_scopes("sending:write")),
    conn=Depends(get_connection),
) -> dict:
    return success_response(await service.mark_email_failed(conn, email_id=email_id, payload=payload))


@router.post("/sending/domain-quota/reserve")
async def reserve_domain_quota(
    payload: dict,
    _: ServiceAuthContext = Depends(require_service_scopes("sending:quota")),
    conn=Depends(get_connection),
) -> dict:
    return success_response(await service.reserve_domain_quota(conn, payload))


@router.post("/intelligence/articles/publish")
async def publish_article(
    payload: dict,
    _: ServiceAuthContext = Depends(require_service_scopes("intelligence:publish")),
    conn=Depends(get_connection),
) -> dict:
    return success_response(await service.publish_article(conn, payload))

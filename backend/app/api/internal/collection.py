from fastapi import APIRouter, Depends, Header

from app.core.errors import AppError
from app.core.responses import success_response
from app.db.pools import get_connection
from app.schemas.internal_collection import ClaimTasksRequest, HeartbeatRequest, MarkFailedRequest, SubmitResultRequest
from app.security.internal import ServiceAuthContext, require_service_scopes
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/collection", tags=["internal-collection"])
service = CollectionService()


@router.post("/tasks/claim")
async def claim_tasks(
    payload: ClaimTasksRequest,
    _: ServiceAuthContext = Depends(require_service_scopes("collection:claim")),
    conn=Depends(get_connection),
) -> dict:
    data = await service.claim_tasks(
        conn,
        service_instance=payload.service_instance,
        limit=payload.limit,
        lease_seconds=payload.lease_seconds,
    )
    return success_response(data)


@router.post("/tasks/{task_id}/heartbeat")
async def heartbeat(
    task_id: str,
    payload: HeartbeatRequest,
    _: ServiceAuthContext = Depends(require_service_scopes("collection:write")),
    conn=Depends(get_connection),
) -> dict:
    data = await service.heartbeat(
        conn,
        task_id=task_id,
        lease_id=payload.lease_id,
        lease_seconds=payload.lease_seconds,
    )
    return success_response(data)


@router.post("/tasks/{task_id}/submit-result")
async def submit_result(
    task_id: str,
    payload: SubmitResultRequest,
    request_id: str | None = Header(default=None, alias="X-Request-Id"),
    auth: ServiceAuthContext = Depends(require_service_scopes("collection:write")),
    conn=Depends(get_connection),
) -> dict:
    if not request_id:
        raise AppError(code="VALIDATION_ERROR", message="缺少 X-Request-Id", status_code=422)
    data = await service.submit_result(
        conn,
        task_id=task_id,
        lease_id=payload.lease_id,
        companies=[item.model_dump() for item in payload.companies],
        contacts=[item.model_dump() for item in payload.contacts],
        competitors=[item.model_dump() for item in payload.competitors],
        request_id=request_id,
        service_name=auth.service_name,
    )
    return success_response(data)


@router.post("/tasks/{task_id}/mark-failed")
async def mark_failed(
    task_id: str,
    payload: MarkFailedRequest,
    _: ServiceAuthContext = Depends(require_service_scopes("collection:write")),
    conn=Depends(get_connection),
) -> dict:
    data = await service.mark_failed(
        conn,
        task_id=task_id,
        lease_id=payload.lease_id,
        error_code=payload.error_code,
        error_message=payload.error_message,
        retryable=payload.retryable,
    )
    return success_response(data)

"""Notification API routes."""

from fastapi import APIRouter, Query

from schemas.intel import NotificationTestPayload
from services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/deliveries")
async def list_deliveries(limit: int = Query(100, ge=1, le=500)):
    """List recent delivery attempts."""
    try:
        service = NotificationService()
        return {"deliveries": await service.list_deliveries(limit=limit)}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/test")
async def send_test_notification(payload: NotificationTestPayload):
    """Send a test notification through a configured channel."""
    try:
        service = NotificationService()
        result = await service.dispatch_test(payload.model_dump())
        return {"delivery": result}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/retry-failed")
async def retry_failed_deliveries(limit: int = Query(25, ge=1, le=100)):
    """Retry failed deliveries that are currently due."""
    try:
        service = NotificationService()
        return {"deliveries": await service.retry_failed_deliveries(limit=limit)}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(delivery_id: int):
    """Retry a single delivery."""
    try:
        service = NotificationService()
        result = await service.retry_delivery(delivery_id)
        return {"delivery": result}
    except Exception as exc:
        return {"error": str(exc)}

"""
Notification delivery service with retries and delivery logging.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta
from email.message import EmailMessage
import hashlib
import hmac
import json
import logging
import smtplib
from typing import Any

import httpx
from sqlalchemy import or_, select

from config import get_settings
from database import async_session_factory
from models.intelligence import NotificationDelivery
from models.workspace import WebhookEndpoint, Workspace

logger = logging.getLogger("notification_service")
settings = get_settings()

DEFAULT_WORKSPACE_SLUG = "default"
RETRY_BACKOFF_SECONDS = (60, 300, 900)


class NotificationService:
    """Dispatch outbound notifications and persist delivery outcomes."""

    def __init__(self):
        self._retry_stop = asyncio.Event()
        self._retry_task: asyncio.Task | None = None

    def start_retry_loop(self) -> asyncio.Task | None:
        """Start the background retry loop if not already running."""
        if self._retry_task and not self._retry_task.done():
            return self._retry_task
        self._retry_stop = asyncio.Event()
        self._retry_task = asyncio.create_task(self._run_retry_loop())
        return self._retry_task

    async def stop_retry_loop(self):
        """Stop the background retry loop."""
        self._retry_stop.set()
        if self._retry_task:
            self._retry_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._retry_task
            self._retry_task = None

    async def dispatch_alert(self, alert_data: dict, alert_id: int | None = None) -> list[dict]:
        """Create delivery records for an alert and attempt immediate dispatch."""
        delivery_ids: list[int] = []
        async with async_session_factory() as session:
            workspace = await self._get_or_create_workspace(session)
            result = await session.execute(
                select(WebhookEndpoint)
                .where(
                    WebhookEndpoint.workspace_id == workspace.id,
                    WebhookEndpoint.enabled.is_(True),
                )
                .order_by(WebhookEndpoint.created_at.asc())
            )
            endpoints = result.scalars().all()
            payload = self._build_payload(
                {
                    "event_type": alert_data.get("alert_type") or "alert",
                    "title": alert_data.get("title") or "Sea Tracker alert",
                    "message": alert_data.get("message") or "",
                    "severity": alert_data.get("severity") or "info",
                    "alert": alert_data,
                }
            )
            for endpoint in endpoints:
                delivery = NotificationDelivery(
                    workspace_id=workspace.id,
                    endpoint_id=endpoint.id,
                    alert_id=alert_id,
                    event_type=payload["event_type"],
                    channel=endpoint.channel,
                    target=endpoint.url,
                    payload=payload,
                    status="pending",
                )
                session.add(delivery)
                await session.flush()
                delivery_ids.append(delivery.id)
            await session.commit()

        deliveries = []
        for delivery_id in delivery_ids:
            result = await self.retry_delivery(delivery_id)
            if result:
                deliveries.append(result)
        return deliveries

    async def dispatch_test(self, payload: dict) -> dict | None:
        """Send and log a direct test notification."""
        async with async_session_factory() as session:
            workspace = await self._get_or_create_workspace(session)
            delivery = NotificationDelivery(
                workspace_id=workspace.id,
                event_type=payload.get("event_type") or "test",
                channel=(payload.get("channel") or "webhook").lower(),
                target=payload.get("target"),
                payload=self._build_payload(payload),
                status="pending",
            )
            session.add(delivery)
            await session.commit()
            delivery_id = delivery.id
        return await self.retry_delivery(delivery_id)

    async def list_deliveries(self, limit: int = 100) -> list[dict]:
        """Return recent delivery log entries."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(NotificationDelivery)
                .order_by(NotificationDelivery.created_at.desc())
                .limit(limit)
            )
            deliveries = result.scalars().all()
            return [self._delivery_to_dict(delivery) for delivery in deliveries]

    async def retry_delivery(self, delivery_id: int) -> dict | None:
        """Retry a single delivery by id."""
        async with async_session_factory() as session:
            delivery = await session.get(NotificationDelivery, delivery_id)
            if not delivery:
                return None
            await self._attempt_delivery(session, delivery)
            await session.commit()
            await session.refresh(delivery)
            return self._delivery_to_dict(delivery)

    async def retry_failed_deliveries(self, limit: int = 25) -> list[dict]:
        """Retry failed deliveries that are due."""
        now = datetime.utcnow()
        async with async_session_factory() as session:
            result = await session.execute(
                select(NotificationDelivery)
                .where(
                    NotificationDelivery.status.in_(("failed", "retrying", "pending")),
                    or_(
                        NotificationDelivery.next_retry_at.is_(None),
                        NotificationDelivery.next_retry_at <= now,
                    ),
                )
                .order_by(NotificationDelivery.created_at.asc())
                .limit(limit)
            )
            deliveries = result.scalars().all()
            results = []
            for delivery in deliveries:
                await self._attempt_delivery(session, delivery)
                results.append(self._delivery_to_dict(delivery))
            await session.commit()
            return results

    async def _run_retry_loop(self):
        while not self._retry_stop.is_set():
            try:
                await self.retry_failed_deliveries(limit=25)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error("Notification retry loop error: %s", exc)
            try:
                await asyncio.wait_for(self._retry_stop.wait(), timeout=30)
            except asyncio.TimeoutError:
                continue

    async def _attempt_delivery(self, session, delivery: NotificationDelivery):
        endpoint = None
        if delivery.endpoint_id:
            endpoint = await session.get(WebhookEndpoint, delivery.endpoint_id)

        channel = (delivery.channel or "webhook").lower()
        target = delivery.target
        signing_secret = endpoint.signing_secret if endpoint else None

        delivery.attempt_count = (delivery.attempt_count or 0) + 1
        delivery.status = "sending"
        delivery.last_error = None
        delivery.response_status = None
        delivery.response_body = None
        delivery.updated_at = datetime.utcnow()
        await session.flush()

        try:
            response_status, response_body = await self._send_channel(
                channel=channel,
                target=target,
                payload=delivery.payload or {},
                signing_secret=signing_secret,
            )
            delivery.response_status = response_status
            delivery.response_body = response_body[:2000] if response_body else None
            delivery.status = "delivered"
            delivery.delivered_at = datetime.utcnow()
            delivery.next_retry_at = None
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Notification delivery failed for %s: %s", delivery.id, exc)
            delivery.last_error = str(exc)
            if delivery.attempt_count < len(RETRY_BACKOFF_SECONDS) + 1:
                delivery.status = "retrying"
                backoff_seconds = RETRY_BACKOFF_SECONDS[delivery.attempt_count - 1]
                delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            else:
                delivery.status = "failed"
                delivery.next_retry_at = None
        delivery.updated_at = datetime.utcnow()
        await session.flush()

    async def _send_channel(
        self,
        *,
        channel: str,
        target: str | None,
        payload: dict,
        signing_secret: str | None = None,
    ) -> tuple[int, str]:
        if channel == "email":
            return await self._send_email(target, payload)
        if channel in {"webhook", "slack", "discord", "telegram"}:
            return await self._send_http(channel, target, payload, signing_secret=signing_secret)
        raise ValueError(f"Unsupported notification channel: {channel}")

    async def _send_http(
        self,
        channel: str,
        target: str | None,
        payload: dict,
        *,
        signing_secret: str | None = None,
    ) -> tuple[int, str]:
        if not target:
            raise ValueError("Missing delivery target")

        url = target
        headers = {"Content-Type": "application/json"}
        body: dict[str, Any]

        if channel == "slack":
            body = {
                "text": f"{payload.get('title')}: {payload.get('message')}",
                "attachments": [
                    {
                        "color": self._severity_color(payload.get("severity")),
                        "fields": [
                            {"title": "Event", "value": payload.get("event_type"), "short": True},
                            {"title": "Severity", "value": payload.get("severity"), "short": True},
                        ],
                    }
                ],
            }
        elif channel == "discord":
            body = {
                "content": f"**{payload.get('title')}**\n{payload.get('message')}",
                "embeds": [
                    {
                        "title": payload.get("title"),
                        "description": payload.get("message"),
                        "color": self._severity_color_int(payload.get("severity")),
                    }
                ],
            }
        elif channel == "telegram":
            url, body, headers = self._build_telegram_request(target, payload)
        else:
            body = payload
            if signing_secret:
                digest = hmac.new(
                    signing_secret.encode("utf-8"),
                    json.dumps(payload, default=str, sort_keys=True).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Sea-Tracker-Signature"] = digest

        async with httpx.AsyncClient(timeout=15.0) as client:
            if channel == "telegram":
                response = await client.post(url, data=body, headers=headers)
            else:
                response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            return response.status_code, response.text or "ok"

    async def _send_email(self, target: str | None, payload: dict) -> tuple[int, str]:
        recipient = (target or "").replace("mailto:", "").strip()
        if not recipient:
            raise ValueError("Missing email recipient")
        if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
            raise ValueError("SMTP settings are not configured")

        message = EmailMessage()
        message["Subject"] = payload.get("title") or "Sea Tracker notification"
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = recipient
        message.set_content(
            "\n".join(
                [
                    f"Event: {payload.get('event_type')}",
                    f"Severity: {payload.get('severity')}",
                    "",
                    payload.get("message") or "",
                ]
            )
        )

        await asyncio.to_thread(self._smtp_send, message)
        return 202, "accepted"

    def _smtp_send(self, message: EmailMessage):
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

    async def _get_or_create_workspace(self, session) -> Workspace:
        result = await session.execute(select(Workspace).where(Workspace.slug == DEFAULT_WORKSPACE_SLUG))
        workspace = result.scalar_one_or_none()
        if workspace:
            return workspace
        workspace = Workspace(slug=DEFAULT_WORKSPACE_SLUG, name="Aegis Maritime Command")
        session.add(workspace)
        await session.flush()
        return workspace

    def _build_payload(self, payload: dict) -> dict:
        return {
            "event_type": payload.get("event_type") or payload.get("alert_type") or "event",
            "title": payload.get("title") or "Sea Tracker event",
            "message": payload.get("message") or "",
            "severity": payload.get("severity") or "info",
            "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
            "metadata": payload.get("metadata") or payload.get("alert") or {},
        }

    def _build_telegram_request(self, target: str, payload: dict) -> tuple[str, dict, dict]:
        headers: dict[str, str] = {}
        if target.startswith("https://api.telegram.org/"):
            url = target
            chat_id = None
        elif ":" in target:
            token, chat_id = target.split(":", 1)
            url = f"https://api.telegram.org/bot{token}/sendMessage"
        else:
            raise ValueError("Telegram target must be a full API URL or token:chat_id")

        body = {
            "text": f"{payload.get('title')}\n{payload.get('message')}",
        }
        if chat_id:
            body["chat_id"] = chat_id
        return url, body, headers

    def _delivery_to_dict(self, delivery: NotificationDelivery) -> dict:
        return {
            "id": delivery.id,
            "workspace_id": delivery.workspace_id,
            "endpoint_id": delivery.endpoint_id,
            "alert_id": delivery.alert_id,
            "event_type": delivery.event_type,
            "channel": delivery.channel,
            "target": delivery.target,
            "status": delivery.status,
            "attempt_count": delivery.attempt_count,
            "response_status": delivery.response_status,
            "response_body": delivery.response_body,
            "last_error": delivery.last_error,
            "next_retry_at": delivery.next_retry_at.isoformat() if delivery.next_retry_at else None,
            "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
            "updated_at": delivery.updated_at.isoformat() if delivery.updated_at else None,
            "payload": delivery.payload or {},
        }

    def _severity_color(self, severity: str | None) -> str:
        if severity == "critical":
            return "#d92d20"
        if severity == "warning":
            return "#f79009"
        return "#1570ef"

    def _severity_color_int(self, severity: str | None) -> int:
        if severity == "critical":
            return 0xD92D20
        if severity == "warning":
            return 0xF79009
        return 0x1570EF

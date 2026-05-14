from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Query, Header
from lnbits.core.services import websocket_manager
from pydantic import BaseModel, Field
from typing import Any

from .crud import get_bitcoinswitch
from .trigger_service import (
    dispatch_trigger_to_device,
    get_configured_pin,
    validate_external_token,
)

bitcoinswitch_triggers_router = APIRouter(prefix="/api/v1/triggers")


class TriggerResponse(BaseModel):
    status: str = "ok"
    trigger_type: str
    switch_id: str
    pin: int
    duration: int
    payload: str


class DeadmanTriggerRequest(BaseModel):
    token: str = Field(..., min_length=1)
    duration: int | None = Field(default=None, ge=1, le=120000)
    comment: str | None = Field(default="deadman_switch")
    source: str = Field(default="deadman")


class NostrTriggerRequest(BaseModel):
    token: str = Field(..., min_length=1)
    duration: int | None = Field(default=None, ge=1, le=120000)
    comment: str | None = Field(default="nostr_trigger")
    pubkey: str | None = None
    event_id: str | None = None
    signature_verified: bool = False


class GenericWebhookPayload(BaseModel):
    """
    Flexible webhook payload for external services (deadman switches, monitoring systems, etc).
    Accepts any JSON structure; token and duration can come from multiple sources.
    """
    class Config:
        extra = "allow"  # Allow additional fields from external services
    
    token: str | None = None  # Can also come from query param or header
    duration: int | None = None  # Can also come from query param or header
    message: str | None = None  # Generic message/comment field
    source: str | None = None  # Service origin for debugging


async def _prepare_trigger(switch_id: str, pin: int, token: str):
    switch = await get_bitcoinswitch(switch_id)
    if not switch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Bitcoinswitch does not exist.",
        )

    if switch.disabled:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"bitcoinswitch {switch_id} is disabled",
        )

    if not websocket_manager.has_connection(switch_id):
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail="No active bitcoinswitch websocket connection.",
        )

    validate_external_token(switch, token)
    configured_switch = get_configured_pin(switch, pin)
    return switch, configured_switch


@bitcoinswitch_triggers_router.post(
    "/deadman/{switch_id}/{pin}", response_model=TriggerResponse
)
async def trigger_from_deadman(
    switch_id: str,
    pin: int,
    data: DeadmanTriggerRequest,
) -> TriggerResponse:
    switch, configured_switch = await _prepare_trigger(switch_id, pin, data.token)
    duration = data.duration if data.duration is not None else configured_switch.duration
    comment = data.comment or data.source

    payload = await dispatch_trigger_to_device(
        switch_id=switch.id,
        pin=pin,
        duration=duration,
        comment=comment,
    )

    return TriggerResponse(
        trigger_type="deadman",
        switch_id=switch.id,
        pin=pin,
        duration=duration,
        payload=payload,
    )


@bitcoinswitch_triggers_router.post(
    "/nostr/{switch_id}/{pin}", response_model=TriggerResponse
)
async def trigger_from_nostr(
    switch_id: str,
    pin: int,
    data: NostrTriggerRequest,
) -> TriggerResponse:
    if not data.signature_verified:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=(
                "NOSTR signature must be verified by an upstream service before "
                "calling this endpoint."
            ),
        )

    switch, configured_switch = await _prepare_trigger(switch_id, pin, data.token)
    duration = data.duration if data.duration is not None else configured_switch.duration

    comment_parts = [data.comment or "nostr_trigger"]
    if data.pubkey:
        comment_parts.append(f"pubkey:{data.pubkey[:12]}")
    if data.event_id:
        comment_parts.append(f"event:{data.event_id[:12]}")
    comment = "|".join(comment_parts)

    payload = await dispatch_trigger_to_device(
        switch_id=switch.id,
        pin=pin,
        duration=duration,
        comment=comment,
    )

    return TriggerResponse(
        trigger_type="nostr",
        switch_id=switch.id,
        pin=pin,
        duration=duration,
        payload=payload,
    )


@bitcoinswitch_triggers_router.post(
    "/webhook/{switch_id}/{pin}", response_model=TriggerResponse
)
async def trigger_from_webhook(
    switch_id: str,
    pin: int,
    data: GenericWebhookPayload,
    token: str | None = Query(None),
    x_webhook_token: str | None = Header(None),
    x_webhook_duration: int | None = Header(None),
) -> TriggerResponse:
    """
    Generic webhook endpoint for external services (deadman switches, monitoring, etc).
    
    Authentication:
    - Token can be provided via: JSON body, query param (?token=...),
      or header (x-webhook-token: ...)
    
    Duration:
    - Can be provided via: JSON body, or header (x-webhook-duration: milliseconds)
    - Falls back to configured duration if not provided
    
    Comment:
    - Extracted from 'message' field in payload, or falls back to 'source' field
    
    Example with cURL (deadman switch alert):
    ```
    curl -X POST https://your-lnbits/bitcoinswitch/api/v1/triggers/webhook/{device_id}/{pin} \\
      -H "content-type: application/json" \\
      -H "x-webhook-token: your_password" \\
      -H "x-webhook-duration: 5000" \\
      -d '{"source": "deadman-monitor", "message": "heartbeat timeout"}'
    ```
    """
    # Determine token from multiple sources (in priority order)
    effective_token = data.token or token or x_webhook_token
    if not effective_token:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Token required. Provide via token field, ?token= query param, or x-webhook-token header.",
        )

    switch, configured_switch = await _prepare_trigger(switch_id, pin, effective_token)
    
    # Determine duration from multiple sources
    effective_duration = (
        x_webhook_duration
        or data.duration
        or configured_switch.duration
    )
    
    # Extract comment from payload
    comment = data.message or data.source or "webhook_trigger"

    payload = await dispatch_trigger_to_device(
        switch_id=switch.id,
        pin=pin,
        duration=effective_duration,
        comment=comment,
    )

    return TriggerResponse(
        trigger_type="webhook",
        switch_id=switch.id,
        pin=pin,
        duration=effective_duration,
        payload=payload,
    )

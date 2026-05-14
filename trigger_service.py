import hmac
from http import HTTPStatus

from fastapi import HTTPException
from lnbits.core.services import websocket_updater

from .models import Bitcoinswitch, Switch


def validate_external_token(bitcoinswitch: Bitcoinswitch, token: str) -> None:
    """Use the existing switch password as shared secret for external triggers."""
    if not bitcoinswitch.password:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=(
                "External triggers require a device password. "
                "Set a password on the switch and use it as the webhook token."
            ),
        )

    if not token or not hmac.compare_digest(bitcoinswitch.password, token):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Invalid external trigger token.",
        )


def get_configured_pin(bitcoinswitch: Bitcoinswitch, pin: int) -> Switch:
    _switch = next((s for s in bitcoinswitch.switches if s.pin == pin), None)
    if not _switch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Switch with pin {pin} not found.",
        )
    return _switch


async def dispatch_trigger_to_device(
    *,
    switch_id: str,
    pin: int,
    duration: int,
    comment: str | None = None,
) -> str:
    payload = f"{pin}-{duration}"
    if comment:
        # ESP32 parser uses '-' as field delimiter, so keep comments delimiter-safe.
        safe_comment = comment.replace("-", "_")
        payload = f"{payload}-{safe_comment}"

    await websocket_updater(switch_id, payload)
    return payload

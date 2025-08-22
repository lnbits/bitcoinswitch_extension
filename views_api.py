from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import websocket_updater
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)

from .crud import (
    create_bitcoinswitch,
    delete_bitcoinswitch,
    get_bitcoinswitch,
    get_bitcoinswitches,
    update_bitcoinswitch,
)
from .models import Bitcoinswitch, CreateBitcoinswitch

bitcoinswitch_api_router = APIRouter(prefix="/api/v1")


@bitcoinswitch_api_router.post("", dependencies=[Depends(require_admin_key)])
async def api_bitcoinswitch_create(data: CreateBitcoinswitch) -> Bitcoinswitch:
    return await create_bitcoinswitch(data)


@bitcoinswitch_api_router.put("/trigger/{switch_id}/{pin}")
async def api_bitcoinswitch_trigger(
    switch_id: str, pin: int, key_info: WalletTypeInfo = Depends(require_admin_key)
) -> None:
    switch = await get_bitcoinswitch(switch_id)
    if not switch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist."
        )
    _switch = next((s for s in switch.switches if s.pin == pin), None)
    if not _switch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Switch with this pin does not exist.",
        )
    if switch.wallet != key_info.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to trigger this switch.",
        )
    await websocket_updater(switch.id, f"{pin}-{_switch.duration}")


@bitcoinswitch_api_router.put("/{bitcoinswitch_id}")
async def api_bitcoinswitch_update(
    data: CreateBitcoinswitch,
    bitcoinswitch_id: str,
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> Bitcoinswitch:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="bitcoinswitch does not exist"
        )
    if bitcoinswitch.wallet != key_info.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to update this bitcoinswitch.",
        )

    for k, v in data.dict().items():
        if v is not None:
            setattr(bitcoinswitch, k, v)

    bitcoinswitch.switches = data.switches
    return await update_bitcoinswitch(bitcoinswitch)


@bitcoinswitch_api_router.get("")
async def api_bitcoinswitchs_retrieve(
    key_info: WalletTypeInfo = Depends(require_invoice_key),
) -> list[Bitcoinswitch]:
    user = await get_user(key_info.wallet.user)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="User does not exist"
        )
    return await get_bitcoinswitches(user.wallet_ids)


@bitcoinswitch_api_router.get("/{bitcoinswitch_id}")
async def api_bitcoinswitch_retrieve(
    bitcoinswitch_id: str, key_info: WalletTypeInfo = Depends(require_admin_key)
) -> Bitcoinswitch:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist"
        )
    if bitcoinswitch.wallet != key_info.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to access this bitcoinswitch.",
        )
    return bitcoinswitch


@bitcoinswitch_api_router.delete("/{bitcoinswitch_id}")
async def api_bitcoinswitch_delete(
    bitcoinswitch_id: str, key_info: WalletTypeInfo = Depends(require_admin_key)
) -> None:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist."
        )
    if bitcoinswitch.wallet != key_info.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to delete this bitcoinswitch.",
        )
    await delete_bitcoinswitch(bitcoinswitch_id)

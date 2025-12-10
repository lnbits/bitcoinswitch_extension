from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from lnbits.core.models import User
from lnbits.core.services import websocket_updater
from lnbits.decorators import check_user_exists

from .crud import (
    create_bitcoinswitch,
    delete_bitcoinswitch,
    get_bitcoinswitch,
    get_bitcoinswitches,
    update_bitcoinswitch,
)
from .models import Bitcoinswitch, BitcoinswitchPublic, CreateBitcoinswitch

bitcoinswitch_api_router = APIRouter(prefix="/api/v1")


@bitcoinswitch_api_router.post("")
async def api_bitcoinswitch_create(
    data: CreateBitcoinswitch, user: User = Depends(check_user_exists)
) -> Bitcoinswitch:
    if data.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=(
                "You do not have permission to create a bitcoinswitch for this wallet."
            ),
        )
    return await create_bitcoinswitch(data)


@bitcoinswitch_api_router.put("/trigger/{switch_id}/{pin}")
async def api_bitcoinswitch_trigger(
    switch_id: str,
    pin: int,
    user: User = Depends(check_user_exists),
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
    if switch.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to trigger this switch.",
        )
    await websocket_updater(switch.id, f"{pin}-{_switch.duration}")


@bitcoinswitch_api_router.put("/{bitcoinswitch_id}")
async def api_bitcoinswitch_update(
    data: CreateBitcoinswitch,
    bitcoinswitch_id: str,
    user: User = Depends(check_user_exists),
) -> Bitcoinswitch:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="bitcoinswitch does not exist"
        )
    if data.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to update this bitcoinswitch.",
        )

    for k, v in data.dict().items():
        if v is not None:
            setattr(bitcoinswitch, k, v)

    bitcoinswitch.switches = data.switches
    return await update_bitcoinswitch(bitcoinswitch)


@bitcoinswitch_api_router.get(
    "/public/{bitcoinswitch_id}", response_model=BitcoinswitchPublic
)
async def api_bitcoinswitch_get_public(bitcoinswitch_id: str) -> Bitcoinswitch:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist."
        )
    return bitcoinswitch


@bitcoinswitch_api_router.get("")
async def api_bitcoinswitchs_retrieve(
    user: User = Depends(check_user_exists),
) -> list[Bitcoinswitch]:
    return await get_bitcoinswitches(user.wallet_ids)


@bitcoinswitch_api_router.get("/{bitcoinswitch_id}")
async def api_bitcoinswitch_retrieve(
    bitcoinswitch_id: str, user: User = Depends(check_user_exists)
) -> Bitcoinswitch:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist"
        )
    if bitcoinswitch.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to access this bitcoinswitch.",
        )
    return bitcoinswitch


@bitcoinswitch_api_router.delete("/{bitcoinswitch_id}")
async def api_bitcoinswitch_delete(
    bitcoinswitch_id: str,
    user: User = Depends(check_user_exists),
) -> None:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist."
        )
    if bitcoinswitch.wallet not in user.wallet_ids:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="You do not have permission to delete this bitcoinswitch.",
        )
    await delete_bitcoinswitch(bitcoinswitch_id)

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
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

bitcoinswitch_api_router = APIRouter(prefix="/api/v1/bitcoinswitch")


@bitcoinswitch_api_router.post("", dependencies=[Depends(require_admin_key)])
async def api_bitcoinswitch_create(data: CreateBitcoinswitch) -> Bitcoinswitch:
    return await create_bitcoinswitch(data)


@bitcoinswitch_api_router.put(
    "/{bitcoinswitch_id}",
    dependencies=[Depends(require_admin_key)],
)
async def api_bitcoinswitch_update(
    data: CreateBitcoinswitch, bitcoinswitch_id: str
) -> Bitcoinswitch:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="bitcoinswitch does not exist"
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
            status_code=HTTPStatus.NOT_FOUND, detail="User does not exist"
        )
    return await get_bitcoinswitches(user.wallet_ids)


@bitcoinswitch_api_router.get(
    "/{bitcoinswitch_id}",
    dependencies=[Depends(require_invoice_key)],
)
async def api_bitcoinswitch_retrieve(bitcoinswitch_id: str) -> Bitcoinswitch:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist"
        )
    return bitcoinswitch


@bitcoinswitch_api_router.delete(
    "/{bitcoinswitch_id}",
    dependencies=[Depends(require_admin_key)],
)
async def api_bitcoinswitch_delete(bitcoinswitch_id: str) -> None:
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bitcoinswitch does not exist."
        )
    await delete_bitcoinswitch(bitcoinswitch_id)

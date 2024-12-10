from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)
from lnbits.helpers import urlsafe_short_hash

from .crud import (
    create_bitcoinswitch,
    delete_bitcoinswitch,
    get_bitcoinswitch,
    get_bitcoinswitches,
    update_bitcoinswitch,
)
from .models import Bitcoinswitch, CreateBitcoinswitch

bitcoinswitch_api_router = APIRouter()


@bitcoinswitch_api_router.post(
    "/api/v1/bitcoinswitch", dependencies=[Depends(require_admin_key)]
)
async def api_bitcoinswitch_create(
    request: Request, data: CreateBitcoinswitch
) -> Bitcoinswitch:
    if len(data.switches) > 0 and data.npub != "":
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Only one switch allowed if using an npub.",
        )

    bitcoinswitch_id = urlsafe_short_hash()

    # compute lnurl for each pin of switch
    url = request.url_for(
        "bitcoinswitch.lnurl_params", bitcoinswitch_id=bitcoinswitch_id
    )
    for switch in data.switches:
        switch.set_lnurl(str(url))

    return await create_bitcoinswitch(bitcoinswitch_id, data)


@bitcoinswitch_api_router.put(
    "/api/v1/bitcoinswitch/{bitcoinswitch_id}",
    dependencies=[Depends(require_admin_key)],
)
async def api_bitcoinswitch_update(
    request: Request, data: CreateBitcoinswitch, bitcoinswitch_id: str
):
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="bitcoinswitch does not exist"
        )
    if len(data.switches) > 0 and data.npub != "":
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Only one switch allowed if using an npub.",
        )

    for k, v in data.dict().items():
        if v is not None:
            setattr(bitcoinswitch, k, v)

    # compute lnurl for each pin of switch
    url = request.url_for(
        "bitcoinswitch.lnurl_params", bitcoinswitch_id=bitcoinswitch_id
    )
    for switch in data.switches:
        switch.set_lnurl(str(url))

    bitcoinswitch.switches = data.switches

    return await update_bitcoinswitch(bitcoinswitch)


@bitcoinswitch_api_router.get("/api/v1/bitcoinswitch")
async def api_bitcoinswitchs_retrieve(
    key_info: WalletTypeInfo = Depends(require_invoice_key),
) -> list[Bitcoinswitch]:
    user = await get_user(key_info.wallet.user)
    assert user, "Bitcoinswitch cannot retrieve user"
    return await get_bitcoinswitches(user.wallet_ids)


@bitcoinswitch_api_router.get(
    "/api/v1/bitcoinswitch/{bitcoinswitch_id}",
    dependencies=[Depends(require_invoice_key)],
)
async def api_bitcoinswitch_retrieve(bitcoinswitch_id: str):
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="bitcoinswitch does not exist"
        )
    return bitcoinswitch


@bitcoinswitch_api_router.delete(
    "/api/v1/bitcoinswitch/{bitcoinswitch_id}",
    dependencies=[Depends(require_admin_key)],
)
async def api_bitcoinswitch_delete(bitcoinswitch_id: str):
    bitcoinswitch = await get_bitcoinswitch(bitcoinswitch_id)
    if not bitcoinswitch:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Lnurldevice does not exist."
        )
    await delete_bitcoinswitch(bitcoinswitch_id)

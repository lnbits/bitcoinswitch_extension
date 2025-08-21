import json
from http import HTTPStatus

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import (
    CallbackUrl,
    LightningInvoice,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayMetadata,
    LnurlPayResponse,
    Max144Str,
    MessageAction,
    MilliSatoshi,
)
from pydantic import parse_obj_as

from .crud import (
    create_bitcoinswitch_payment,
    delete_bitcoinswitch_payment,
    get_bitcoinswitch,
    get_bitcoinswitch_payment,
    update_bitcoinswitch_payment,
)

bitcoinswitch_lnurl_router = APIRouter(prefix="/api/v1/lnurl")


@bitcoinswitch_lnurl_router.get("/{bitcoinswitch_id}")
async def lnurl_params(
    request: Request, bitcoinswitch_id: str, pin: str
) -> LnurlPayResponse | LnurlErrorResponse:
    switch = await get_bitcoinswitch(bitcoinswitch_id)
    if not switch:
        return LnurlErrorResponse(
            reason=f"bitcoinswitch {bitcoinswitch_id} not found on this server"
        )

    _switch = next((_s for _s in switch.switches if _s.pin == int(pin)), None)
    if not _switch:
        return LnurlErrorResponse(reason="Extra params wrong")

    price_msat = int(
        (
            await fiat_amount_as_satoshis(float(_switch.amount), switch.currency)
            if switch.currency != "sat"
            else float(_switch.amount)
        )
        * 1000
    )

    bitcoinswitch_payment = await create_bitcoinswitch_payment(
        bitcoinswitch_id=switch.id,
        payload=str(_switch.duration),
        amount_msat=price_msat,
        pin=int(pin),
        payment_hash="not yet set",
    )
    if not bitcoinswitch_payment:
        return LnurlErrorResponse(reason="Could not create payment.")

    url = str(
        request.url_for(
            "bitcoinswitch.lnurl_callback", payment_id=bitcoinswitch_payment.id
        )
    )
    max_sendable = price_msat * 360 if _switch.variable else price_msat
    res = LnurlPayResponse(
        callback=parse_obj_as(CallbackUrl, url),
        minSendable=MilliSatoshi(price_msat),
        maxSendable=MilliSatoshi(max_sendable),
        metadata=LnurlPayMetadata(json.dumps([["text/plain", switch.title]])),
    )
    if _switch.comment is True:
        res.commentAllowed = 255

    return res


@bitcoinswitch_lnurl_router.get(
    "/cb/{payment_id}",
    status_code=HTTPStatus.OK,
    name="bitcoinswitch.lnurl_callback",
)
async def lnurl_callback(
    payment_id: str,
    amount: int | None = Query(None),
    comment: str | None = Query(None),
) -> LnurlPayActionResponse | LnurlErrorResponse:
    bitcoinswitch_payment = await get_bitcoinswitch_payment(payment_id)
    if not bitcoinswitch_payment:
        return LnurlErrorResponse(reason="Switch payment not found.")
    switch = await get_bitcoinswitch(bitcoinswitch_payment.bitcoinswitch_id)
    if not switch:
        await delete_bitcoinswitch_payment(payment_id)
        return LnurlErrorResponse(reason="Switch not found.")

    if not amount:
        return LnurlErrorResponse(reason="No amount specified")

    memo = f"{switch.title} ({bitcoinswitch_payment.payload} ms)"
    if comment:
        memo += f" - {comment}"

    metadata = LnurlPayMetadata(json.dumps([["text/plain", switch.title]]))

    payment = await create_invoice(
        wallet_id=switch.wallet,
        amount=int(amount / 1000),
        unhashed_description=metadata.encode(),
        memo=memo,
        extra={
            "tag": "Switch",
            "pin": str(bitcoinswitch_payment.pin),
            "amount": str(int(amount)),
            "comment": comment,
            "id": payment_id,
        },
    )
    bitcoinswitch_payment.payment_hash = payment.payment_hash
    await update_bitcoinswitch_payment(bitcoinswitch_payment)

    message = f"{int(amount / 1000)}sats sent"
    if switch.password and switch.password != comment:
        message = f"{message}, but password was incorrect! :("

    return LnurlPayActionResponse(
        pr=parse_obj_as(LightningInvoice, payment.bolt11),
        successAction=MessageAction(message=parse_obj_as(Max144Str, message)),
    )

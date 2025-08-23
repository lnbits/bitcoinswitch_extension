import json

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import (
    CallbackUrl,
    InvalidLnurl,
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

from .crud import create_switch_payment, get_bitcoinswitch

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
    if switch.disabled:
        return LnurlErrorResponse(
            reason=f"bitcoinswitch {bitcoinswitch_id} is disabled"
        )

    _switch = next((_s for _s in switch.switches if _s.pin == int(pin)), None)
    if not _switch:
        return LnurlErrorResponse(reason=f"Switch with pin {pin} not found.")

    price_msat = int(
        (
            await fiat_amount_as_satoshis(float(_switch.amount), switch.currency)
            if switch.currency != "sat"
            else float(_switch.amount)
        )
        * 1000
    )
    # let the max be 100x the min if variable pricing is enabled
    max_sendable = price_msat * 100 if _switch.variable else price_msat
    url = request.url_for("bitcoinswitch.lnurl_cb", switch_id=bitcoinswitch_id, pin=pin)
    try:
        callback_url = parse_obj_as(CallbackUrl, str(url))
    except InvalidLnurl:
        return LnurlErrorResponse(reason=f"Invalid LNURL callback URL: {url!s}")
    res = LnurlPayResponse(
        callback=callback_url,
        minSendable=MilliSatoshi(price_msat),
        maxSendable=MilliSatoshi(max_sendable),
        metadata=LnurlPayMetadata(json.dumps([["text/plain", switch.title]])),
    )
    if _switch.comment is True:
        res.commentAllowed = 255
    return res


@bitcoinswitch_lnurl_router.get("/cb/{switch_id}/{pin}", name="bitcoinswitch.lnurl_cb")
async def lnurl_callback(
    switch_id: str,
    pin: int,
    amount: int | None = Query(None),
    comment: str | None = Query(None),
) -> LnurlPayActionResponse | LnurlErrorResponse:
    if comment and len(comment) > 255:
        return LnurlErrorResponse(reason="Comment too long, max 255 characters.")
    if not amount:
        return LnurlErrorResponse(reason="No amount specified.")

    switch = await get_bitcoinswitch(switch_id)
    if not switch:
        return LnurlErrorResponse(reason="Switch not found.")
    if switch.disabled:
        return LnurlErrorResponse(reason=f"bitcoinswitch {switch_id} is disabled")
    _switch = next((_s for _s in switch.switches if _s.pin == int(pin)), None)
    if not _switch:
        return LnurlErrorResponse(reason=f"Switch with pin {pin} not found.")

    memo = f"{switch.title} (pin: {pin})"
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
            "pin": pin,
            "comment": comment,
        },
    )

    await create_switch_payment(
        payment_hash=payment.payment_hash,
        switch_id=switch.id,
        pin=pin,
        amount_msat=amount,
    )

    message = f"{int(amount / 1000)}sats sent"
    if switch.password and switch.password != comment:
        message = f"{message}, but password was incorrect! :("

    return LnurlPayActionResponse(
        pr=parse_obj_as(LightningInvoice, payment.bolt11),
        successAction=MessageAction(message=parse_obj_as(Max144Str, message)),
        disposable=switch.disposable,
    )

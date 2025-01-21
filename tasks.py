import asyncio

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.tasks import register_invoice_listener

from .crud import (
    get_bitcoinswitch_payment,
    update_bitcoinswitch_payment,
)


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_bitcoinswitch")

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "Switch":
        return

    bitcoinswitch_payment = await get_bitcoinswitch_payment(payment.extra["id"])

    if not bitcoinswitch_payment or bitcoinswitch_payment.payment_hash == "paid":
        return

    bitcoinswitch_payment.payment_hash = bitcoinswitch_payment.payload
    bitcoinswitch_payment = await update_bitcoinswitch_payment(bitcoinswitch_payment)
    payload = bitcoinswitch_payment.payload

    variable = payment.extra.get("variable")
    if variable is True:
        payload = str(
            (int(payload) / int(bitcoinswitch_payment.sats))
            * int(payment.extra["amount"])
        )
    payload = f"{bitcoinswitch_payment.pin}-{payload}"

    comment = payment.extra.get("comment")
    if comment:
        payload = f"{payload}-{comment}"

    return await websocket_updater(
        bitcoinswitch_payment.bitcoinswitch_id,
        payload,
    )

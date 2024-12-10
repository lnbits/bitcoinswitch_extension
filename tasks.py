import asyncio

from bech32 import bech32_decode, convertbits

from nostr.filter import Filter, Filters
from nostr.key import PublicKey
from nostr.message_type import ClientMessageType
from nostr.relay_manager import RelayManager
from nostr.subscription import Subscription
from nostr.event import Event

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.tasks import register_invoice_listener
from lnbits.settings import settings

from .crud import (
    get_bitcoinswitch_payment,
    update_bitcoinswitch_payment,
    get_public_keys,
    get_switch_from_npub
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
    variable = payment.extra.get("variable", False)
    if variable:
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

async def get_nostr_events():
    pub_keys = await get_public_keys()
    target_keys_hex = [
        decode_npub_to_hex(pk) if pk.startswith("npub") else pk
        for pk in pub_keys
    ]

    relay_url = f"wss://localhost:{settings.port}/nostrclient/api/v1/relay"
    relay_manager = RelayManager()
    relay_manager.add_relay(relay_url)

    zap_filter = Filter(kinds=[9735], pubkey_refs=target_keys_hex)
    filters = Filters([zap_filter])

    relay_manager.add_subscription("bitcoinswitch_zaps", filters)
    relay_manager.open_connections()

    try:
        while True:
            while relay_manager.message_pool.has_events():
                event_message = relay_manager.message_pool.get_event()
                event = event_message.event
                for tag in event.tags:
                    if tag[0] == "p" and tag[1] in target_keys_hex:
                        switch = await get_switch_from_npub(event.sender)
                        if not switch:
                            continue
                        payload = int(event.amount)
                        if switch.variable:
                            payload = str(
                                (switch.amount / int(event.amount)) * switch.amount
                            )
                        payload = f"{switch.pin}-{payload}"
                        await websocket_updater(
                            switch.id,
                            payload,
                        )
                        break
            await asyncio.sleep(1)
    finally:
        relay_manager.close_connections()

def decode_npub_to_hex(npub):
    hrp, data = bech32_decode(npub)
    if hrp != "npub" or data is None:
        raise ValueError(f"Invalid npub: {npub}")
    decoded_bytes = bytes(convertbits(data, 5, 8, False))
    return decoded_bytes.hex()

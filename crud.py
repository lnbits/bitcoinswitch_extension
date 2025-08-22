from datetime import datetime, timezone

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import (
    Bitcoinswitch,
    BitcoinswitchPayment,
    CreateBitcoinswitch,
)

db = Database("ext_bitcoinswitch")


async def create_bitcoinswitch(
    data: CreateBitcoinswitch,
) -> Bitcoinswitch:
    bitcoinswitch_id = urlsafe_short_hash()
    bitcoinswitch_key = urlsafe_short_hash()
    device = Bitcoinswitch(
        id=bitcoinswitch_id,
        key=bitcoinswitch_key,
        title=data.title,
        wallet=data.wallet,
        currency=data.currency,
        switches=data.switches,
        password=data.password,
    )
    await db.insert("bitcoinswitch.switch", device)
    return device


async def update_bitcoinswitch(device: Bitcoinswitch) -> Bitcoinswitch:
    device.updated_at = datetime.now(timezone.utc)
    await db.update("bitcoinswitch.switch", device)
    return device


async def get_bitcoinswitch(bitcoinswitch_id: str) -> Bitcoinswitch | None:
    return await db.fetchone(
        "SELECT * FROM bitcoinswitch.switch WHERE id = :id",
        {"id": bitcoinswitch_id},
        Bitcoinswitch,
    )


async def get_bitcoinswitches(wallet_ids: list[str]) -> list[Bitcoinswitch]:
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"""
        SELECT * FROM bitcoinswitch.switch WHERE wallet IN ({q})
        ORDER BY id
        """,
        model=Bitcoinswitch,
    )


async def delete_bitcoinswitch(bitcoinswitch_id: str) -> None:
    await db.execute(
        "DELETE FROM bitcoinswitch.switch WHERE id = :id",
        {"id": bitcoinswitch_id},
    )


async def create_switch_payment(
    payment_hash: str,
    switch_id: str,
    pin: int,
    amount_msat: int = 0,
) -> BitcoinswitchPayment:
    payment_id = urlsafe_short_hash()
    payment = BitcoinswitchPayment(
        id=payment_id,
        payment_hash=payment_hash,
        bitcoinswitch_id=switch_id,
        pin=pin,
        sats=amount_msat,
    )
    await db.insert("bitcoinswitch.payment", payment)
    return payment


async def update_switch_payment(
    switch_payment: BitcoinswitchPayment,
) -> BitcoinswitchPayment:
    switch_payment.updated_at = datetime.now(timezone.utc)
    await db.update("bitcoinswitch.payment", switch_payment)
    return switch_payment


async def delete_switch_payment(switch_payment_id: str) -> None:
    await db.execute(
        "DELETE FROM bitcoinswitch.payment WHERE id = :id",
        {"id": switch_payment_id},
    )


async def get_switch_payment(
    bitcoinswitchpayment_id: str,
) -> BitcoinswitchPayment | None:
    return await db.fetchone(
        "SELECT * FROM bitcoinswitch.payment WHERE id = :id",
        {"id": bitcoinswitchpayment_id},
        BitcoinswitchPayment,
    )


async def get_switch_payment_by_payment_hash(
    payment_hash: str,
) -> BitcoinswitchPayment | None:
    return await db.fetchone(
        "SELECT * FROM bitcoinswitch.payment WHERE payment_hash = :h",
        {"h": payment_hash},
    )


async def get_switch_payments(
    bitcoinswitch_ids: list[str],
) -> list[BitcoinswitchPayment]:
    if len(bitcoinswitch_ids) == 0:
        return []
    q = ",".join([f"'{w}'" for w in bitcoinswitch_ids])
    return await db.fetchall(
        f"""
        SELECT * FROM bitcoinswitch.payment WHERE deviceid IN ({q})
        ORDER BY id
        """,
        model=BitcoinswitchPayment,
    )

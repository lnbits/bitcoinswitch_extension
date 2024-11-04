from datetime import datetime, timezone
from typing import Optional

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import (
    Bitcoinswitch,
    BitcoinswitchPayment,
    CreateBitcoinswitch,
)

db = Database("ext_bitcoinswitch")


async def create_bitcoinswitch(
    bitcoinswitch_id: str,
    data: CreateBitcoinswitch,
) -> Bitcoinswitch:
    bitcoinswitch_key = urlsafe_short_hash()
    device = Bitcoinswitch(
        id=bitcoinswitch_id,
        key=bitcoinswitch_key,
        title=data.title,
        wallet=data.wallet,
        currency=data.currency,
        switches=data.switches,
    )
    await db.insert("bitcoinswitch.switch", device)
    return device


async def update_bitcoinswitch(device: Bitcoinswitch) -> Bitcoinswitch:
    device.updated_at = datetime.now(timezone.utc)
    await db.update("bitcoinswitch.switch", device)
    return device


async def get_bitcoinswitch(bitcoinswitch_id: str) -> Optional[Bitcoinswitch]:
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


async def create_bitcoinswitch_payment(
    bitcoinswitch_id: str,
    payment_hash: str,
    payload: str,
    pin: int,
    amount_msat: int = 0,
) -> BitcoinswitchPayment:
    bitcoinswitchpayment_id = urlsafe_short_hash()
    payment = BitcoinswitchPayment(
        id=bitcoinswitchpayment_id,
        bitcoinswitch_id=bitcoinswitch_id,
        payload=payload,
        pin=pin,
        payment_hash=payment_hash,
        sats=amount_msat,
    )
    await db.insert("bitcoinswitch.payment", payment)
    return payment


async def update_bitcoinswitch_payment(
    bitcoinswitch_payment: BitcoinswitchPayment,
) -> BitcoinswitchPayment:
    bitcoinswitch_payment.updated_at = datetime.now(timezone.utc)
    await db.update("bitcoinswitch.payment", bitcoinswitch_payment)
    return bitcoinswitch_payment


async def delete_bitcoinswitch_payment(bitcoinswitch_payment_id: str) -> None:
    await db.execute(
        "DELETE FROM bitcoinswitch.payment WHERE id = :id",
        {"id": bitcoinswitch_payment_id},
    )


async def get_bitcoinswitch_payment(
    bitcoinswitchpayment_id: str,
) -> Optional[BitcoinswitchPayment]:
    return await db.fetchone(
        "SELECT * FROM bitcoinswitch.payment WHERE id = :id",
        {"id": bitcoinswitchpayment_id},
        BitcoinswitchPayment,
    )


async def get_bitcoinswitch_payments(
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


async def get_bitcoinswitch_payment_by_payhash(
    payhash: str,
) -> Optional[BitcoinswitchPayment]:
    return await db.fetchone(
        "SELECT * FROM bitcoinswitch.payment WHERE payhash = :payhash",
        {"payhash": payhash},
    )


async def get_bitcoinswitch_payment_by_payload(
    payload: str,
) -> Optional[BitcoinswitchPayment]:
    return await db.fetchone(
        "SELECT * FROM bitcoinswitch.payment WHERE payload = :payload",
        {"payload": payload},
        BitcoinswitchPayment,
    )


async def get_recent_bitcoinswitch_payment(
    payload: str,
) -> Optional[BitcoinswitchPayment]:
    return await db.fetchone(
        """
        SELECT * FROM bitcoinswitch.bitcoinswitchpayment
        WHERE payload = :payload ORDER BY timestamp DESC LIMIT 1
        """,
        {"payload": payload},
        BitcoinswitchPayment,
    )

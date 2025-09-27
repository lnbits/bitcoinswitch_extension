from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class Switch(BaseModel):
    amount: float = 0.0
    duration: int = 0
    pin: int = 0
    comment: bool = False
    variable: bool = False
    label: str | None = None

    # Taproot Assets fields (optional, default to disabled)
    accepts_assets: bool = False
    accepted_asset_ids: List[str] = Field(default_factory=list)


class CreateBitcoinswitch(BaseModel):
    title: str
    wallet: str
    currency: str
    switches: list[Switch]
    password: str | None = None
    disabled: bool = False
    disposable: bool = True


class Bitcoinswitch(BaseModel):
    id: str
    title: str
    wallet: str
    currency: str
    switches: list[Switch]
    password: str | None = None
    disabled: bool = False
    disposable: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # obsolete field, do not use anymore
    # should be deleted from the database in the future
    key: str = ""


class BitcoinswitchPayment(BaseModel):
    id: str
    bitcoinswitch_id: str
    payment_hash: str
    pin: int
    sats: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # TODO: deprecated do not use this field anymore
    # should be deleted from the database in the future
    payload: str = ""

    # Taproot Assets fields (optional, default to Lightning payment)
    is_taproot: bool = False
    asset_id: Optional[str] = None
    asset_amount: Optional[int] = None

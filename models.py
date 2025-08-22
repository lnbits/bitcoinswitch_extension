from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Switch(BaseModel):
    amount: float = 0.0
    duration: int = 0
    pin: int = 0
    comment: bool = False
    variable: bool = False
    label: Optional[str] = None


class CreateBitcoinswitch(BaseModel):
    title: str
    wallet: str
    currency: str
    switches: list[Switch]
    password: Optional[str] = None


class Bitcoinswitch(BaseModel):
    id: str
    title: str
    wallet: str
    currency: str
    key: str
    switches: list[Switch]
    password: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BitcoinswitchPayment(BaseModel):
    id: str
    payment_hash: str
    bitcoinswitch_id: str
    payload: str
    pin: int
    sats: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Switch(BaseModel):
    amount: float = 0.0
    duration: int = 0
    pin: int = 0
    comment: bool = False
    variable: bool = False
    label: str | None = None


class CreateBitcoinswitch(BaseModel):
    title: str
    wallet: str
    currency: str
    switches: list[Switch]
    password: str | None = None


class Bitcoinswitch(BaseModel):
    id: str
    title: str
    wallet: str
    currency: str
    key: str
    switches: list[Switch]
    password: str | None = None
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

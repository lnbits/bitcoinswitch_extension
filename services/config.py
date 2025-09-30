"""BitcoinSwitch configuration."""
import os
from pydantic import BaseModel


class BitcoinSwitchConfig(BaseModel):
    rate_tolerance: float = float(os.getenv("BITCOINSWITCH_RATE_TOLERANCE", "0.05"))
    rate_validity_minutes: int = int(os.getenv("BITCOINSWITCH_RATE_VALIDITY_MINUTES", "5"))
    rate_refresh_seconds: int = int(os.getenv("BITCOINSWITCH_RATE_REFRESH_SECONDS", "60"))
    http_timeout: float = float(os.getenv("BITCOINSWITCH_HTTP_TIMEOUT", "10.0"))
    taproot_quote_expiry: int = int(os.getenv("BITCOINSWITCH_TAPROOT_QUOTE_EXPIRY", "300"))
    taproot_payment_expiry: int = int(os.getenv("BITCOINSWITCH_TAPROOT_PAYMENT_EXPIRY", "3600"))
    max_comment_length: int = int(os.getenv("BITCOINSWITCH_MAX_COMMENT_LENGTH", "639"))

# Global config instance
config = BitcoinSwitchConfig()
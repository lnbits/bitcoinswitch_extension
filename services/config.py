"""BitcoinSwitch configuration."""
from typing import Dict, Any
import os
from pydantic import BaseModel, Field


class BitcoinSwitchConfig(BaseModel):
    """Configuration settings for BitcoinSwitch extension."""

    # Rate management
    rate_tolerance: float = Field(
        default=float(os.getenv("BITCOINSWITCH_RATE_TOLERANCE", "0.05")),
        description="Allowed deviation in exchange rates (e.g., 0.05 = 5%)"
    )
    rate_validity_minutes: int = Field(
        default=int(os.getenv("BITCOINSWITCH_RATE_VALIDITY_MINUTES", "5")),
        description="How long a rate quote remains valid"
    )
    rate_refresh_seconds: int = Field(
        default=int(os.getenv("BITCOINSWITCH_RATE_REFRESH_SECONDS", "60")),
        description="How often to refresh rates"
    )

    # HTTP timeouts
    http_timeout: float = Field(
        default=float(os.getenv("BITCOINSWITCH_HTTP_TIMEOUT", "10.0")),
        description="HTTP request timeout in seconds"
    )

    # Taproot settings
    taproot_quote_expiry: int = Field(
        default=int(os.getenv("BITCOINSWITCH_TAPROOT_QUOTE_EXPIRY", "300")),
        description="How long a Taproot RFQ quote remains valid in seconds (default 5 minutes)"
    )
    taproot_payment_expiry: int = Field(
        default=int(os.getenv("BITCOINSWITCH_TAPROOT_PAYMENT_EXPIRY", "3600")),
        description="How long a Taproot payment invoice remains valid in seconds (default 1 hour)"
    )

    # Comment settings
    max_comment_length: int = Field(
        default=int(os.getenv("BITCOINSWITCH_MAX_COMMENT_LENGTH", "639")),
        description="Maximum length for payment comments (BOLT-11 limit is 639 bytes)"
    )

# Global config instance
config = BitcoinSwitchConfig()
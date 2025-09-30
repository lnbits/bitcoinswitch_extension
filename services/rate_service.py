"""
Rate service for managing exchange rates between assets and sats.

This service handles the rate management functionality for LNURL and Taproot Assets,
including rate discovery, validation, and expiration checks. It interacts with the
Taproot Assets API to get current market rates and validates them against configured
tolerances.

Key features:
- Real-time rate discovery through RFQ (Request for Quote)
- Rate validation with configurable tolerance
- Rate expiration management
"""
# Standard library imports
from datetime import datetime, timedelta, timezone

# Third-party imports
import httpx
from loguru import logger

# Local/LNbits imports
from lnbits.core.crud import get_wallet
from lnbits.settings import settings
from .config import config


class RateService:
    """
    Service for managing asset exchange rates between Taproot Assets and Bitcoin.

    This service provides methods to:
    - Discover current market rates through RFQ
    - Validate rates against tolerance thresholds
    - Check rate expiration

    All methods are static as this is a utility service without state.
    """

    @staticmethod
    async def get_current_rate(
        asset_id: str,
        wallet_id: str,
        user_id: str,
        asset_amount: int = 1
    ) -> float | None:
        """
        Get current exchange rate for an asset using RFQ quote.

        Creates a minimal RFQ (Request for Quote) buy order to discover the current rate
        without creating an actual invoice. Uses the Taproot Assets API to get the
        current market rate for the specified asset.

        Args:
            asset_id: The Taproot Asset ID to get the rate for
            wallet_id: LNbits wallet ID for API authentication
            user_id: LNbits user ID associated with the wallet
            asset_amount: Amount of assets to get quote for (default: 1)

        Returns:
            float: The current rate in sats per asset unit, or None if rate fetch fails

        Note:
            The rate returned is in satoshis per one unit of the asset.
            For example, if the rate is 1000, it means 1 unit of the asset = 1000 sats.
        """
        try:
            # Get wallet for API key
            wallet = await get_wallet(wallet_id)
            if not wallet:
                logger.error(f"Wallet {wallet_id} not found")
                return None

            # Build API URL
            base_url = settings.lnbits_baseurl
            if not base_url.startswith("http"):
                base_url = f"http://{base_url}"

            url = f"{base_url}/taproot_assets/api/v1/taproot/rate/{asset_id}"

            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params={"amount": asset_amount},
                    headers={"X-Api-Key": wallet.adminkey},
                    timeout=config.http_timeout
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get("rate_per_unit"):
                        rate = data["rate_per_unit"]
                        logger.debug(f"Got rate from API: {rate} sats/unit for {asset_amount} units of {asset_id[:8]}...")
                        return rate
                    else:
                        logger.warning(f"No rate returned from API: {data.get('error', 'Unknown error')}")
                        return None
                else:
                    logger.error(f"API request failed with status {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Failed to fetch RFQ rate for asset {asset_id}: {e}")
            return None

    @staticmethod
    def is_rate_within_tolerance(
        quoted_rate: float,
        current_rate: float,
        tolerance: float = None
    ) -> bool:
        """
        Check if current rate is within acceptable tolerance of quoted rate.

        Calculates the percentage deviation between the quoted and current rates
        and compares it against the configured tolerance threshold.

        Args:
            quoted_rate: The original quoted rate to compare against
            current_rate: The current market rate
            tolerance: float | None custom tolerance (defaults to config.rate_tolerance)

        Returns:
            bool: True if the current rate is within tolerance of quoted rate

        Note:
            The tolerance is expressed as a decimal (e.g., 0.05 = 5% tolerance).
            The comparison uses absolute deviation, so both upward and downward
            price movements are treated equally.
        """
        if quoted_rate <= 0:
            return False

        tolerance = tolerance or config.rate_tolerance
        deviation = abs(current_rate - quoted_rate) / quoted_rate
        within_tolerance = deviation <= tolerance

        logger.debug(
            f"Rate check: quoted={quoted_rate:.8f}, current={current_rate:.8f}, "
            f"deviation={deviation:.2%}, tolerance={tolerance:.2%}, "
            f"within_tolerance={within_tolerance}"
        )

        return within_tolerance

    @staticmethod
    def is_rate_expired(quoted_at: datetime) -> bool:
        """
        Check if a rate quote has expired based on configured validity period.

        Compares the age of the quote against the configured rate_validity_minutes
        to determine if it's still valid. Handles both timezone-aware and naive
        datetime objects by ensuring UTC timezone consistency.

        Args:
            quoted_at: The timestamp when the rate was originally quoted

        Returns:
            bool: True if the rate has expired, False if still valid

        Note:
            If quoted_at is None or the quote age exceeds rate_validity_minutes,
            the rate is considered expired. The method ensures timezone consistency
            by converting naive datetimes to UTC.
        """
        if not quoted_at:
            return True

        # Ensure quoted_at is timezone-aware
        if quoted_at.tzinfo is None:
            quoted_at = quoted_at.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - quoted_at
        expired = age > timedelta(minutes=config.rate_validity_minutes)

        logger.debug(
            f"Rate age check: quoted_at={quoted_at}, age={age}, "
            f"validity={config.rate_validity_minutes}min, expired={expired}"
        )

        return expired
"""
Simplified integration layer for Taproot Assets extension.

Provides direct access to Taproot Assets functionality when available,
with graceful fallback when the extension is not installed.
"""

from loguru import logger

# Try to import taproot assets functionality
try:
    from lnbits.extensions.taproot_assets.models import TaprootInvoiceRequest
    from lnbits.extensions.taproot_assets.services.invoice_service import InvoiceService
    from lnbits.extensions.taproot_assets.services.asset_service import AssetService
    from lnbits.core.models import Wallet, WalletTypeInfo
    from lnbits.core.models.wallets import KeyType

    TAPROOT_AVAILABLE = True
    logger.info("Taproot Assets extension is available")

except ImportError as e:
    TAPROOT_AVAILABLE = False
    logger.info(f"Taproot Assets extension not available: {e}")

    # Provide stub classes/functions when not available
    class TaprootInvoiceRequest:
        pass

    class InvoiceService:
        @staticmethod
        async def create_invoice(*args, **kwargs):
            raise Exception("Taproot Assets extension not installed")

    class AssetService:
        @staticmethod
        async def list_assets(*args, **kwargs):
            return []


async def create_taproot_invoice(
    asset_id: str,
    amount: int,
    description: str,
    wallet_id: str,
    user_id: str,
    expiry: int | None = None,
    peer_pubkey: str | None = None,
    extra: dict | None = None
) -> dict | None:
    """
    Create a Taproot Asset invoice using the taproot_assets extension.

    Returns:
        dict with invoice data if successful, None if failed
    """
    if not TAPROOT_AVAILABLE:
        logger.error("Cannot create taproot invoice - extension not available")
        return None

    try:
        # Create the invoice request
        invoice_request = TaprootInvoiceRequest(
            asset_id=asset_id,
            amount=amount,
            description=description,
            expiry=expiry or 3600,
            peer_pubkey=peer_pubkey,
            extra=extra or {}
        )

        # Use InvoiceService directly from taproot_assets extension
        invoice_response = await InvoiceService.create_invoice(
            data=invoice_request,
            user_id=user_id,
            wallet_id=wallet_id
        )

        # Convert response to dict format expected by bitcoinswitch
        return {
            "payment_hash": invoice_response.payment_hash,
            "payment_request": invoice_response.payment_request,
            "checking_id": invoice_response.checking_id,
            "is_rfq": True
        }

    except Exception as e:
        logger.error(f"Failed to create taproot invoice: {e}")
        return None


async def get_asset_name(asset_id: str, wallet_info: WalletTypeInfo) -> str:
    """Get human-readable asset name."""
    if not TAPROOT_AVAILABLE:
        return f"asset {asset_id[:8]}..."

    try:
        assets = await AssetService.list_assets(wallet_info)
        for asset in assets:
            if asset.asset_id == asset_id:
                return asset.name or f"asset {asset_id[:8]}..."
        return f"asset {asset_id[:8]}..."
    except Exception:
        return f"asset {asset_id[:8]}..."
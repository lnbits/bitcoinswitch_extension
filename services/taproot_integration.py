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


async def create_rfq_invoice(
    asset_id: str,
    amount: int,
    description: str,
    wallet_id: str,
    user_id: str,
    extra: dict,
    peer_pubkey: str | None = None,
    expiry: int | None = None
) -> tuple[dict | None, str | None]:
    """
    Create a Taproot Asset invoice using RFQ (Request for Quote) process.

    This restores the original working parameter order and return format.
    """
    try:
        # Validate inputs
        if not asset_id:
            return None, "Asset ID is required"

        if amount <= 0:
            return None, f"Amount must be greater than 0, got {amount}"

        # Create the invoice request with original parameter order
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

        # Return in original format (tuple with result and error)
        result = {
            "payment_hash": invoice_response.payment_hash,
            "payment_request": invoice_response.payment_request,
            "checking_id": invoice_response.checking_id,
            "is_rfq": True
        }

        return result, None

    except Exception as e:
        logger.error(f"Failed to create RFQ invoice: {e}")
        return None, str(e)


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
    """Create a Taproot Asset invoice using the taproot_assets extension."""
    # Use the working RFQ method internally
    result, error = await create_rfq_invoice(
        asset_id=asset_id,
        amount=amount,
        description=description,
        wallet_id=wallet_id,
        user_id=user_id,
        extra=extra or {},
        peer_pubkey=peer_pubkey,
        expiry=expiry
    )

    if error:
        logger.error(f"Failed to create taproot invoice: {error}")
        return None

    return result


async def get_asset_name(asset_id: str, wallet_info: WalletTypeInfo) -> str:
    """Get human-readable asset name."""
    try:
        assets = await AssetService.list_assets(wallet_info)
        for asset in assets:
            if asset.asset_id == asset_id:
                return asset.name or f"asset {asset_id[:8]}..."
        return f"asset {asset_id[:8]}..."
    except Exception:
        return f"asset {asset_id[:8]}..."
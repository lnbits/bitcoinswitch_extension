"""
Integration service for Taproot Assets extension functionality.

This module provides integration with the LNbits Taproot Assets extension,
handling availability checks and invoice creation through RFQ (Request for Quote).
It manages the interaction between BitcoinSwitch and the Taproot Assets extension,
ensuring proper error handling and validation.

Key features:
- Taproot Assets extension availability checks
- RFQ invoice creation for asset payments
- Structured error handling with detailed error reporting
"""

from loguru import logger
from pydantic import BaseModel

from lnbits.core.crud import get_installed_extensions


class TaprootError(BaseModel):
    """
    Error class for structured Taproot integration error reporting.

    Attributes:
        code: Machine-readable error code for programmatic handling
        message: Human-readable error message
        details: Optional dictionary of additional error context

    Example:
        error = TaprootError(
            code="INVALID_AMOUNT",
            message="Amount must be positive",
            details={"amount": -100}
        )
    """
    code: str
    message: str
    details: dict | None = None

    def __str__(self) -> str:
        """Returns formatted error string with code and message."""
        return f"{self.code}: {self.message}"


class TaprootIntegration:
    """
    Integration service for Taproot Assets functionality.

    This class provides static methods to interact with the Taproot Assets
    extension, handling common operations like availability checks and
    invoice creation. It includes comprehensive error handling and
    validation for all operations.
    """

    @staticmethod
    async def is_taproot_available() -> tuple[bool, TaprootError | None]:
        """
        Check if Taproot Assets extension is installed and active.

        Verifies that the Taproot Assets extension is both installed in LNbits
        and currently active. This check should be performed before attempting
        any Taproot Assets operations.

        Returns:
            Tuple containing:
            - bool: True if extension is available and active
            - TaprootError | None: Error details if check fails, None if successful

        Example:
            available, error = await TaprootIntegration.is_taproot_available()
            if not available:
                logger.error(f"Taproot not available: {error}")
        """
        try:
            extensions = await get_installed_extensions()
            is_available = any(ext.id == "taproot_assets" and ext.active for ext in extensions)

            if not is_available:
                return False, TaprootError(
                    code="TAPROOT_NOT_AVAILABLE",
                    message="Taproot Assets extension is not installed or not active",
                    details={"installed_extensions": [ext.id for ext in extensions]}
                )

            return True, None

        except Exception as e:
            error = TaprootError(
                code="TAPROOT_CHECK_FAILED",
                message="Failed to check taproot availability",
                details={"error": str(e)}
            )
            logger.warning(str(error))
            return False, error

    @staticmethod
    async def create_rfq_invoice(
        asset_id: str,
        amount: int,
        description: str,
        wallet_id: str,
        user_id: str,
        extra: dict,
        peer_pubkey: str | None = None,
        expiry: int | None = None
    ) -> tuple[dict | None, TaprootError | None]:
        """
        Create a Taproot Asset invoice using RFQ (Request for Quote) process.

        Creates an invoice that can be paid with either sats or the specified asset
        using the RFQ system. This method handles both the creation process and
        all necessary validation.

        Args:
            asset_id: Taproot Asset ID for the invoice
            amount: Amount of the asset to request
            description: Payment description
            wallet_id: LNbits wallet ID for the recipient
            user_id: LNbits user ID of the recipient
            extra: Additional metadata for the invoice
            peer_pubkey: str | None specific peer to use for the trade
            expiry: int | None invoice expiry time in seconds

        Returns:
            Tuple containing:
            - dict | None: Invoice data if successful, with keys:
                - payment_hash: Hash of the payment
                - payment_request: BOLT11 invoice
                - checking_id: ID for checking payment status
                - is_rfq: Always True for RFQ invoices
            - TaprootError | None: Error details if creation fails

        Note:
            The peer_pubkey is optional - if not provided, the invoice service
            will automatically discover and select an appropriate peer.
        """
        try:
            # Check if extension is available first
            taproot_available, error = await TaprootIntegration.is_taproot_available()
            if not taproot_available:
                return None, error

            # Validate inputs
            if not asset_id:
                return None, TaprootError(
                    code="INVALID_ASSET_ID",
                    message="Asset ID is required"
                )

            if amount <= 0:
                return None, TaprootError(
                    code="INVALID_AMOUNT",
                    message="Amount must be greater than 0",
                    details={"amount": amount}
                )

            # Import taproot assets services (only if available)
            try:
                from lnbits.extensions.taproot_assets.services.invoice_service import InvoiceService
                from lnbits.extensions.taproot_assets.models import TaprootInvoiceRequest
            except ImportError as e:
                return None, TaprootError(
                    code="TAPROOT_IMPORT_ERROR",
                    message="Failed to import Taproot Assets services",
                    details={"error": str(e)}
                )

            # Create the invoice request
            request = TaprootInvoiceRequest(
                asset_id=asset_id,
                amount=amount,
                description=description,
                expiry=expiry,
                peer_pubkey=peer_pubkey,  # Can be None - invoice service will find it
                extra=extra
            )

            try:
                # Let the invoice service handle everything including peer discovery
                response = await InvoiceService.create_invoice(
                    data=request,
                    user_id=user_id,
                    wallet_id=wallet_id
                )

                return {
                    "payment_hash": response.payment_hash,
                    "payment_request": response.payment_request,
                    "checking_id": response.checking_id,
                    "is_rfq": True
                }, None

            except Exception as e:
                error = TaprootError(
                    code="RFQ_CREATION_FAILED",
                    message="Failed to create RFQ invoice",
                    details={
                        "error": str(e),
                        "asset_id": asset_id,
                        "amount": amount,
                        "wallet_id": wallet_id
                    }
                )
                logger.error(str(error))
                return None, error

        except Exception as e:
            error = TaprootError(
                code="UNEXPECTED_ERROR",
                message="Unexpected error during RFQ invoice creation",
                details={"error": str(e)}
            )
            logger.error(str(error))
            return None, error
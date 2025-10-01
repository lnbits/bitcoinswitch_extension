import json

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice, websocket_manager
from lnbits.core.crud import get_wallet
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import (
    CallbackUrl,
    InvalidLnurl,
    LightningInvoice,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayMetadata,
    LnurlPayResponse,
    Max144Str,
    MessageAction,
    MilliSatoshi,
)
from pydantic import parse_obj_as
from loguru import logger

from .crud import create_switch_payment, get_bitcoinswitch
from .services.taproot_integration import (
    TAPROOT_AVAILABLE as TAPROOT_SERVICE_AVAILABLE,
    create_rfq_invoice,
    get_asset_name
)
from .services.rate_service import RateService
from .services.config import config
# Check if taproot_assets extension is available
import importlib
TAPROOT_AVAILABLE = importlib.util.find_spec("lnbits.extensions.taproot_assets") is not None

if not TAPROOT_AVAILABLE:
    logger.info("Taproot services not available - running in Lightning-only mode")

bitcoinswitch_lnurl_router = APIRouter(prefix="/api/v1/lnurl")


@bitcoinswitch_lnurl_router.get("/{bitcoinswitch_id}")
async def lnurl_params(
    request: Request, bitcoinswitch_id: str, pin: str
):
    switch = await get_bitcoinswitch(bitcoinswitch_id)
    if not switch:
        return LnurlErrorResponse(
            reason=f"bitcoinswitch {bitcoinswitch_id} not found on this server"
        )
    if switch.disabled:
        return LnurlErrorResponse(
            reason=f"bitcoinswitch {bitcoinswitch_id} is disabled"
        )

    _switch = next((_s for _s in switch.switches if _s.pin == int(pin)), None)
    if not _switch:
        return LnurlErrorResponse(reason=f"Switch with pin {pin} not found.")

    price_msat = int(
        (
            await fiat_amount_as_satoshis(float(_switch.amount), switch.currency)
            if switch.currency != "sat"
            else float(_switch.amount)
        )
        * 1000
    )
    # let the max be 100x the min if variable pricing is enabled
    max_sendable = price_msat * 100 if _switch.variable else price_msat

    # Build callback URL with asset support information if applicable
    base_url = request.url_for("bitcoinswitch.lnurl_cb", switch_id=bitcoinswitch_id, pin=pin)
    callback_url_str = str(base_url)

    # Encode Taproot Asset support in callback URL parameters
    if TAPROOT_AVAILABLE and hasattr(_switch, 'accepts_assets') and _switch.accepts_assets:
        if _switch.accepted_asset_ids:
            # Encode asset support in URL parameters
            asset_ids_param = "|".join(_switch.accepted_asset_ids)
            callback_url_str += f"?supports_assets=true&asset_ids={asset_ids_param}"
            logger.info(f"Switch {bitcoinswitch_id} callback URL encoded with taproot assets: {_switch.accepted_asset_ids}")

    try:
        callback_url = parse_obj_as(CallbackUrl, callback_url_str)
    except InvalidLnurl:
        return LnurlErrorResponse(reason=f"Invalid LNURL callback URL: {callback_url_str!s}")

    res = LnurlPayResponse(
        callback=callback_url,
        minSendable=MilliSatoshi(price_msat),
        maxSendable=MilliSatoshi(max_sendable),
        metadata=LnurlPayMetadata(json.dumps([["text/plain", switch.title]])),
    )
    if _switch.comment is True:
        res.commentAllowed = 255

    return res


@bitcoinswitch_lnurl_router.get("/cb/{switch_id}/{pin}", name="bitcoinswitch.lnurl_cb")
async def lnurl_callback(
    switch_id: str,
    pin: int,
    amount: int | None = Query(None),
    comment: str | None = Query(None),
    asset_id: str | None = Query(None),
) -> LnurlPayActionResponse | LnurlErrorResponse:
    if comment and len(comment) > 255:
        return LnurlErrorResponse(reason="Comment too long, max 255 characters.")
    if not amount:
        return LnurlErrorResponse(reason="No amount specified.")

    switch = await get_bitcoinswitch(switch_id)
    if not switch:
        return LnurlErrorResponse(reason="Switch not found.")
    if switch.disabled:
        return LnurlErrorResponse(reason=f"bitcoinswitch {switch_id} is disabled")
    _switch = next((_s for _s in switch.switches if _s.pin == int(pin)), None)
    if not _switch:
        return LnurlErrorResponse(reason=f"Switch with pin {pin} not found.")

    if not switch.disposable and not websocket_manager.has_connection(switch_id):
        return LnurlErrorResponse(reason="No active bitcoinswitch connections.")

    # Check for Taproot Asset payment
    logger.info(f"TAPROOT CHECK: TAPROOT_AVAILABLE={TAPROOT_AVAILABLE}, asset_id={asset_id}")
    if hasattr(_switch, 'accepts_assets'):
        logger.info(f"Switch accepts_assets: {_switch.accepts_assets}")
    else:
        logger.info("Switch has no accepts_assets attribute")

    if TAPROOT_AVAILABLE and asset_id and hasattr(_switch, 'accepts_assets') and _switch.accepts_assets:
        logger.info(f"Switch accepted_asset_ids: {_switch.accepted_asset_ids}")
        try:
            if asset_id in _switch.accepted_asset_ids:
                logger.info(f"Processing taproot asset payment for {asset_id}")
                return await handle_taproot_payment(
                    switch, _switch, switch_id, pin, amount, comment, asset_id
                )
            else:
                logger.warning(f"Asset {asset_id} not in accepted list: {_switch.accepted_asset_ids}")
        except Exception as e:
            logger.error(f"Taproot payment failed, falling back to Lightning: {e}")
    else:
        logger.info("Taproot conditions not met, using Lightning payment")

    # Standard Lightning payment (original logic)
    memo = f"{switch.title} (pin: {pin})"
    if comment:
        memo += f" - {comment}"

    metadata = LnurlPayMetadata(json.dumps([["text/plain", switch.title]]))

    payment = await create_invoice(
        wallet_id=switch.wallet,
        amount=int(amount / 1000),
        unhashed_description=metadata.encode(),
        memo=memo,
        extra={
            "tag": "Switch",
            "pin": pin,
            "comment": comment,
        },
    )

    await create_switch_payment(
        payment_hash=payment.payment_hash,
        switch_id=switch.id,
        pin=pin,
        amount_msat=amount,
    )

    message = f"{int(amount / 1000)}sats sent"
    if switch.password and switch.password != comment:
        message = f"{message}, but password was incorrect! :("

    return LnurlPayActionResponse(
        pr=parse_obj_as(LightningInvoice, payment.bolt11),
        successAction=MessageAction(message=parse_obj_as(Max144Str, message)),
        disposable=switch.disposable,
    )


async def handle_taproot_payment(switch, _switch, switch_id, pin, amount, comment, asset_id):
    """Handle Taproot Asset payment - only called if taproot services available."""
    if not TAPROOT_AVAILABLE:
        raise Exception("Taproot services not available")

    # Get wallet for user ID
    wallet = await get_wallet(switch.wallet)
    if not wallet:
        return LnurlErrorResponse(reason="Wallet not found")

    # Calculate asset amount using RFQ rate if available, otherwise use switch config
    requested_sats = amount / 1000
    asset_amount = await calculate_asset_amount_with_rfq(
        asset_id=asset_id,
        requested_sats=requested_sats,
        switch_amount=int(_switch.amount),
        wallet_id=switch.wallet,
        user_id=wallet.user
    )

    logger.info(f"TAPROOT PAYMENT:")
    logger.info(f"  - Lightning amount requested: {amount} msat ({requested_sats} sats)")
    logger.info(f"  - Calculated asset_amount: {asset_amount}")
    logger.info(f"  - Asset ID: {asset_id}")

    # Get peer_pubkey from asset channel info (like the direct UI does)
    peer_pubkey = None
    try:
        from lnbits.extensions.taproot_assets.services.asset_service import AssetService
        from lnbits.core.models import WalletTypeInfo
        from lnbits.core.models.wallets import KeyType

        wallet_info = WalletTypeInfo(key_type=KeyType.admin, wallet=wallet)
        assets = await AssetService.list_assets(wallet_info)

        # Find the asset and get its peer_pubkey
        for asset in assets:
            if asset.get("asset_id") == asset_id and asset.get("channel_info") and asset["channel_info"].get("peer_pubkey"):
                peer_pubkey = asset["channel_info"]["peer_pubkey"]
                logger.info(f"  - Found peer_pubkey: {peer_pubkey[:16]}...")
                break

        if not peer_pubkey:
            logger.warning(f"  - No peer_pubkey found for asset {asset_id}")

    except Exception as e:
        logger.error(f"Failed to get peer_pubkey: {e}")

    # Create Taproot Asset invoice using original working API
    taproot_result, taproot_error = await create_rfq_invoice(
        asset_id=asset_id,
        amount=asset_amount,
        description=f"{switch.title} (pin: {pin})",
        wallet_id=switch.wallet,
        user_id=wallet.user,
        extra={
            "tag": "Switch",
            "pin": pin,
            "comment": comment,
        },
        peer_pubkey=peer_pubkey,
        expiry=config.taproot_payment_expiry
    )

    if not taproot_result or taproot_error:
        raise Exception(f"Failed to create RFQ invoice: {taproot_error}")

    # Create payment record with taproot fields
    payment_record = await create_switch_payment(
        payment_hash=taproot_result["payment_hash"],
        switch_id=switch.id,
        pin=pin,
        amount_msat=amount,
    )

    # Update with taproot-specific fields if available
    if hasattr(payment_record, 'is_taproot'):
        payment_record.is_taproot = True
        payment_record.asset_id = asset_id
        payment_record.asset_amount = asset_amount
        from .crud import update_switch_payment
        await update_switch_payment(payment_record)

    # Get asset name for user-friendly message
    from lnbits.core.models import WalletTypeInfo
    from lnbits.core.models.wallets import KeyType
    wallet_info = WalletTypeInfo(key_type=KeyType.admin, wallet=wallet)
    asset_name = await get_asset_name(asset_id, wallet_info)

    # Clean success message without redundant "units requested" text
    if switch.password and switch.password != comment:
        message = "Password was incorrect! :("
    else:
        message = f"{asset_amount} {asset_name} sent"

    return LnurlPayActionResponse(
        pr=parse_obj_as(LightningInvoice, taproot_result["payment_request"]),
        successAction=MessageAction(message=parse_obj_as(Max144Str, message)),
        disposable=switch.disposable,
    )


async def calculate_asset_amount_with_rfq(
    asset_id: str,
    requested_sats: float,
    switch_amount: int,
    wallet_id: str,
    user_id: str
) -> int:
    """Calculate asset amount using RFQ rate or fallback to switch configuration."""
    try:
        # Try to get current rate via RFQ
        current_rate = await RateService.get_current_rate(
            asset_id=asset_id,
            wallet_id=wallet_id,
            user_id=user_id,
            asset_amount=switch_amount
        )

        if current_rate and current_rate > 0:
            # Calculate asset amount based on real market rate
            # current_rate is sats per asset unit
            asset_amount = int(requested_sats / current_rate)
            logger.info(f"RFQ rate calculation: {requested_sats} sats / {current_rate} sats/asset = {asset_amount} assets")
            return max(1, asset_amount)
        else:
            logger.warning(f"No valid RFQ rate available, using switch config: {switch_amount} assets")
            return switch_amount

    except Exception as e:
        logger.error(f"RFQ rate lookup failed: {e}, using switch config: {switch_amount} assets")
        return switch_amount



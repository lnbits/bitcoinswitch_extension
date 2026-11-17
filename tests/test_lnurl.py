from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from lnbits.wallets.fake import FakeWallet
from lnurl import LnurlErrorResponse, LnurlPayActionResponse

from .. import views_lnurl
from ..models import Bitcoinswitch, Switch


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["sat", "EUR"])
@pytest.mark.parametrize(
    "variable, amount_msat, accepted",
    [
        (False, 1000, False),
        (False, 15999, False),
        (False, 16000, True),
        (False, 16001, False),
        (True, 1000, False),
        (True, 15999, False),
        (True, 16000, True),
        (True, 32000, True),
        (True, 1600000, True),
        (True, 1600001, False),
    ],
)
async def test_callback_amount_bounds(
    monkeypatch, currency, variable, amount_msat, accepted
):
    switch = Bitcoinswitch(
        id="test-switch",
        title="Test switch",
        wallet="test-wallet",
        currency=currency,
        switches=[
            Switch(amount=16 if currency == "sat" else 0.01, pin=5, variable=variable)
        ],
    )
    monkeypatch.setattr(
        views_lnurl, "get_bitcoinswitch", AsyncMock(return_value=switch)
    )
    monkeypatch.setattr(
        views_lnurl, "fiat_amount_as_satoshis", AsyncMock(return_value=16)
    )
    monkeypatch.setattr(
        views_lnurl.websocket_manager, "has_connection", Mock(return_value=True)
    )
    invoice = await FakeWallet().create_invoice(amount=amount_msat // 1000)
    create_invoice = AsyncMock(
        return_value=SimpleNamespace(
            payment_hash=invoice.checking_id, bolt11=invoice.payment_request
        )
    )
    create_payment = AsyncMock()
    monkeypatch.setattr(views_lnurl, "create_invoice", create_invoice)
    monkeypatch.setattr(views_lnurl, "create_switch_payment", create_payment)

    response = await views_lnurl.lnurl_callback(switch.id, 5, amount_msat, None)

    if accepted:
        assert isinstance(response, LnurlPayActionResponse)
        create_invoice.assert_awaited_once()
        assert create_invoice.await_args is not None
        assert create_invoice.await_args.kwargs["amount"] == amount_msat // 1000
        create_payment.assert_awaited_once()
    else:
        assert isinstance(response, LnurlErrorResponse)
        create_invoice.assert_not_awaited()
        create_payment.assert_not_awaited()

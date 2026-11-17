from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, create_autospec

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from lnbits.core.models import Payment, User
from lnbits.db import Database
from lnbits.settings import settings
from lnbits.wallets.fake import FakeWallet
from lnurl import LnurlErrorResponse, LnurlPayActionResponse

from .. import crud, migrations, tasks, views_api, views_lnurl
from ..models import Bitcoinswitch, CreateBitcoinswitch, Switch


@pytest.fixture
def switch():
    return Bitcoinswitch(
        id="public-switch-id",
        title="Test switch",
        wallet="wallet-id",
        currency="sat",
        switches=[Switch(pin=16, amount=5000, duration=1000)],
    )


@pytest.mark.asyncio
async def test_device_keys_are_created_and_migrated(monkeypatch, tmp_path, switch):
    monkeypatch.setattr(settings, "lnbits_data_folder", str(tmp_path))
    db = Database("ext_bitcoinswitch")
    monkeypatch.setattr(crud, "db", db)
    try:
        for migration in (
            migrations.m001_initial,
            migrations.m002_add_password,
            migrations.m003_disabled,
            migrations.m004_disposable,
        ):
            await migration(db)
        switch.key = ""
        await db.insert("bitcoinswitch.switch", switch)
        other = switch.model_copy(update={"id": "other-switch", "key": "old-key"})
        await db.insert("bitcoinswitch.switch", other)

        await migrations.m005_device_channel_keys(db)

        devices = await crud.get_bitcoinswitches([switch.wallet])
        keys = {device.key for device in devices}
        assert len(keys) == 2
        assert all(len(key) == 43 for key in keys)
        assert "old-key" not in keys
        assert {device.id for device in devices} == {switch.id, other.id}
        created = await crud.create_bitcoinswitch(
            CreateBitcoinswitch.model_validate(switch.model_dump())
        )
        saved = await crud.get_bitcoinswitch(created.id)
        assert saved is not None
        assert saved.key == created.key
        assert len(saved.key) == 43
        assert saved.key not in keys
    finally:
        await db.engine.dispose()


@pytest.mark.asyncio
async def test_public_response_excludes_device_key(monkeypatch, switch):
    monkeypatch.setattr(views_api, "get_bitcoinswitch", AsyncMock(return_value=switch))
    app = FastAPI()
    app.include_router(views_api.bitcoinswitch_api_router)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/public/{switch.id}")
    assert response.status_code == 200
    assert "key" not in response.json()
    assert switch.key not in response.text


@pytest.mark.asyncio
async def test_triggers_use_device_key(monkeypatch, switch):
    send = AsyncMock()
    monkeypatch.setattr(views_api, "get_bitcoinswitch", AsyncMock(return_value=switch))
    monkeypatch.setattr(views_api, "websocket_updater", send)
    await views_api.api_bitcoinswitch_trigger(
        switch.id, 16, create_autospec(User, instance=True, wallet_ids=[switch.wallet])
    )
    send.assert_awaited_once_with(switch.key, "16-1000")

    send.reset_mock()
    monkeypatch.setattr(tasks, "get_bitcoinswitch", AsyncMock(return_value=switch))
    monkeypatch.setattr(
        tasks,
        "get_switch_payment_by_payment_hash",
        AsyncMock(return_value=SimpleNamespace(bitcoinswitch_id=switch.id, pin=16)),
    )
    monkeypatch.setattr(tasks.websocket_manager, "send", send)
    await tasks.on_invoice_paid(
        create_autospec(
            Payment, instance=True, payment_hash="payment-hash", extra={"tag": "Switch"}
        )
    )
    send.assert_awaited_once_with(switch.key, "16-1000")


@pytest.mark.asyncio
async def test_callback_requires_device_channel_connection(monkeypatch, switch):
    monkeypatch.setattr(
        views_lnurl, "get_bitcoinswitch", AsyncMock(return_value=switch)
    )
    monkeypatch.setattr(
        views_lnurl.websocket_manager,
        "has_connection",
        lambda channel: channel == switch.id,
    )
    create_invoice = AsyncMock()
    monkeypatch.setattr(views_lnurl, "create_invoice", create_invoice)

    response = await views_lnurl.lnurl_callback(switch.id, 16, 5000000, None)

    assert isinstance(response, LnurlErrorResponse)
    assert response.reason == "No active bitcoinswitch connections."
    create_invoice.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["sat", "USD"])
@pytest.mark.parametrize(
    ("variable", "amount", "accepted"),
    [
        (False, None, False),
        (False, 0, False),
        (False, -1000, False),
        (False, 1000, False),
        (False, 4999999, False),
        (False, 5000000, True),
        (False, 5000001, False),
        (True, 4999999, False),
        (True, 5000000, True),
        (True, 10000000, True),
        (True, 500000000, True),
        (True, 500000001, False),
    ],
)
async def test_callback_payment_range(
    monkeypatch, switch, currency, variable, amount, accepted
):
    switch.currency = currency
    switch.switches[0].variable = variable
    monkeypatch.setattr(
        views_lnurl, "get_bitcoinswitch", AsyncMock(return_value=switch)
    )
    monkeypatch.setattr(
        views_lnurl, "fiat_amount_as_satoshis", AsyncMock(return_value=5000)
    )
    connected = Mock(return_value=True)
    monkeypatch.setattr(views_lnurl.websocket_manager, "has_connection", connected)
    invoice = await FakeWallet().create_invoice(5000, "Test switch")
    create_invoice = AsyncMock(
        return_value=SimpleNamespace(
            payment_hash="payment-hash", bolt11=invoice.payment_request
        )
    )
    save_payment = AsyncMock()
    monkeypatch.setattr(views_lnurl, "create_invoice", create_invoice)
    monkeypatch.setattr(views_lnurl, "create_switch_payment", save_payment)

    response = await views_lnurl.lnurl_callback(switch.id, 16, amount, None)

    if accepted:
        assert isinstance(response, LnurlPayActionResponse)
        connected.assert_called_once_with(switch.key)
        create_invoice.assert_awaited_once()
        assert create_invoice.await_args is not None
        assert create_invoice.await_args.kwargs["amount"] == amount // 1000
        save_payment.assert_awaited_once_with(
            payment_hash="payment-hash", switch_id=switch.id, pin=16, amount_msat=amount
        )
    else:
        assert isinstance(response, LnurlErrorResponse)
        create_invoice.assert_not_awaited()
        save_payment.assert_not_awaited()

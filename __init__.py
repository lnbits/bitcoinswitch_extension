import asyncio

from fastapi import APIRouter
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices, get_nostr_events
from .views import bitcoinswitch_generic_router
from .views_api import bitcoinswitch_api_router
from .views_lnurl import bitcoinswitch_lnurl_router

bitcoinswitch_ext: APIRouter = APIRouter(
    prefix="/bitcoinswitch", tags=["bitcoinswitch"]
)
bitcoinswitch_ext.include_router(bitcoinswitch_generic_router)
bitcoinswitch_ext.include_router(bitcoinswitch_api_router)
bitcoinswitch_ext.include_router(bitcoinswitch_lnurl_router)

bitcoinswitch_static_files = [
    {
        "path": "/bitcoinswitch/static",
        "name": "bitcoinswitch_static",
    }
]
scheduled_tasks: list[asyncio.Task] = []


def bitcoinswitch_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def bitcoinswitch_start():
    from lnbits.tasks import create_permanent_unique_task
    task1 = create_permanent_unique_task("ext_bitcoinswitch", wait_for_paid_invoices)
    task2 = create_permanent_unique_task("ext_bitcoinswitch", get_nostr_events)
    scheduled_tasks.extend([task1, task2])


__all__ = [
    "db",
    "bitcoinswitch_ext",
    "bitcoinswitch_static_files",
    "bitcoinswitch_start",
    "bitcoinswitch_stop",
]

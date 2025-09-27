"""
Bitcoin Switch Extension with Taproot Assets Support.

This extension allows controlling GPIO pins through Lightning Network payments
and Taproot Asset transfers. It provides:
- Standard Lightning Network payments
- Taproot Asset payments
- Real-time payment processing
- WebSocket updates
- Variable time control
"""
import asyncio
from typing import List, Dict, Any

from fastapi import APIRouter
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import bitcoinswitch_generic_router
from .views_api import bitcoinswitch_api_router
from .views_lnurl import bitcoinswitch_lnurl_router

bitcoinswitch_ext: APIRouter = APIRouter(
    prefix="/bitcoinswitch", tags=["bitcoinswitch"]
)
bitcoinswitch_ext.include_router(bitcoinswitch_generic_router)
bitcoinswitch_ext.include_router(bitcoinswitch_api_router)
bitcoinswitch_ext.include_router(bitcoinswitch_lnurl_router)

# Static file configuration
bitcoinswitch_static_files: List[Dict[str, str]] = [
    {
        "path": "/bitcoinswitch/static",
        "name": "bitcoinswitch_static",
    }
]

# Track background tasks
scheduled_tasks: List[asyncio.Task] = []


def bitcoinswitch_start() -> None:
    """
    Start the Bitcoin Switch extension.

    Initializes:
    - Payment processing task
    - WebSocket handlers
    - Background processes
    """
    try:
        from lnbits.tasks import create_permanent_unique_task

        task = create_permanent_unique_task(
            "ext_bitcoinswitch",
            wait_for_paid_invoices
        )
        scheduled_tasks.append(task)
        logger.info("Bitcoin Switch extension started successfully")
    except Exception as e:
        logger.error(
            "Failed to start Bitcoin Switch extension",
            error=str(e)
        )
        raise


def bitcoinswitch_stop() -> None:
    """
    Stop the Bitcoin Switch extension.

    Cleans up:
    - Cancels background tasks
    - Closes connections
    - Stops payment processing
    """
    for task in scheduled_tasks:
        try:
            task.cancel()
            logger.debug(f"Cancelled task: {task.get_name()}")
        except Exception as e:
            logger.warning(
                "Error cancelling task",
                task=task.get_name() if task else "Unknown",
                error=str(e)
            )

    scheduled_tasks.clear()
    logger.info("Bitcoin Switch extension stopped successfully")


__all__ = [
    "bitcoinswitch_ext",
    "bitcoinswitch_start",
    "bitcoinswitch_static_files",
    "bitcoinswitch_stop",
    "db",
]

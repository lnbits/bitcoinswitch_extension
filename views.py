from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

from .crud import get_bitcoinswitch

bitcoinswitch_generic_router = APIRouter()


def bitcoinswitch_renderer():
    return template_renderer(["bitcoinswitch/templates"])


@bitcoinswitch_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return bitcoinswitch_renderer().TemplateResponse(
        "bitcoinswitch/index.html",
        {"request": request, "user": user.json()},
    )


@bitcoinswitch_generic_router.get("/public/{switch_id}", response_class=HTMLResponse)
async def public(
    switch_id: str, request: Request, user: User = Depends(check_user_exists)
):
    switch = await get_bitcoinswitch(switch_id)
    if not switch:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Switch not found")

    return bitcoinswitch_renderer().TemplateResponse(
        "bitcoinswitch/public.html",
        {"request": request, "user": user.json(), "switch": switch.json()},
    )

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

bitcoinswitch_generic_router = APIRouter()


def bitcoinswitch_renderer():
    return template_renderer(["bitcoinswitch/templates"])


@bitcoinswitch_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return bitcoinswitch_renderer().TemplateResponse(
        "bitcoinswitch/index.html",
        {"request": request, "user": user.json()},
    )

from fastapi import APIRouter, Depends
from lnbits.core.views.generic import index, index_public
from lnbits.decorators import check_user_exists

bitcoinswitch_generic_router = APIRouter()


bitcoinswitch_generic_router.add_api_route(
    "/", methods=["GET"], endpoint=index, dependencies=[Depends(check_user_exists)]
)

bitcoinswitch_generic_router.add_api_route(
    "/public/{switch_id}", methods=["GET"], endpoint=index_public
)

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from vstitchDTO.adminReturnRequestDTO import UpdateReturnStatusRequestDTO
from vstitchDTO.adminReturnResponseDTO import AdminReturnListResponseDTO, AdminReturnResponseDTO
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.adminReturnService import AdminReturnService


class AdminReturnApi:
    """Exposes the /admin/returns endpoints. Admin-JWT-gated at the router
    level, same mechanism as every other admin router.
    """

    def __init__(self):
        self.admin_return_service = AdminReturnService()
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/returns", self.list_returns, methods=["GET"], response_model=AdminReturnListResponseDTO
        )
        self.router.add_api_route(
            "/returns/{vstitch_return_order_id}/status",
            self.update_return_status,
            methods=["PATCH"],
            response_model=AdminReturnResponseDTO,
        )

    # Sync def - see orderapi.py's create_order for the full rationale.
    def list_returns(
        self,
        status: Optional[str] = Query(default=None),
        after_id: Optional[int] = Query(default=None, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        try:
            return self.admin_return_service.list_returns(status, after_id, limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading returns. Please try again later.",
            )

    def update_return_status(
        self,
        update_return_status_request_dto: UpdateReturnStatusRequestDTO,
        vstitch_return_order_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.admin_return_service.update_return_status(
                vstitch_return_order_id, update_return_status_request_dto.status, current_admin["admin_username"]
            )
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while updating the return status. Please try again later.",
            )


admin_return_api = AdminReturnApi()
admin_return_router = admin_return_api.router

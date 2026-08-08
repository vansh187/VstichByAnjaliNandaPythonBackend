from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from vstitchDatabase.couponPersistence import InvalidCouponError
from vstitchDatabase.uniqueConstraintError import UniqueConstraintError
from vstitchDTO.couponRequestDTO import CreateCouponRequestDTO, UpdateCouponRequestDTO
from vstitchDTO.couponResponseDTO import CouponListResponseDTO, CouponResponseDTO
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.couponService import CouponService


class AdminCouponApi:
    """Exposes /admin/coupons - admin CRUD backing the "Active Coupons"
    marketing screen. Admin-JWT-gated at the router level, same mechanism
    as every other admin router.
    """

    def __init__(self):
        self.coupon_service = CouponService()
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/coupons", self.list_coupons, methods=["GET"], response_model=CouponListResponseDTO
        )
        self.router.add_api_route(
            "/coupons", self.create_coupon, methods=["POST"], response_model=CouponResponseDTO, status_code=201
        )
        self.router.add_api_route(
            "/coupons/{vstitch_coupon_id}", self.get_coupon, methods=["GET"], response_model=CouponResponseDTO
        )
        self.router.add_api_route(
            "/coupons/{vstitch_coupon_id}", self.update_coupon, methods=["PATCH"], response_model=CouponResponseDTO
        )

    def list_coupons(
        self,
        after_id: Optional[int] = Query(default=None, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        try:
            return self.coupon_service.list_coupons_admin(after_id, limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading coupons. Please try again later.",
            )

    def create_coupon(
        self,
        create_coupon_request_dto: CreateCouponRequestDTO,
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.coupon_service.create_coupon(create_coupon_request_dto, current_admin["admin_username"])
        except UniqueConstraintError as conflict_error:
            raise HTTPException(status_code=409, detail=str(conflict_error))
        except InvalidCouponError as invalid_coupon_error:
            raise HTTPException(status_code=422, detail=str(invalid_coupon_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while creating the coupon. Please try again later.",
            )

    def get_coupon(self, vstitch_coupon_id: int = Path(..., ge=1)):
        try:
            return self.coupon_service.get_coupon(vstitch_coupon_id)
        except ValueError as not_found_error:
            raise HTTPException(status_code=404, detail=str(not_found_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading the coupon. Please try again later.",
            )

    def update_coupon(
        self,
        update_coupon_request_dto: UpdateCouponRequestDTO,
        vstitch_coupon_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.coupon_service.update_coupon(
                vstitch_coupon_id, update_coupon_request_dto, current_admin["admin_username"]
            )
        except InvalidCouponError as invalid_coupon_error:
            raise HTTPException(status_code=422, detail=str(invalid_coupon_error))
        except ValueError as not_found_error:
            raise HTTPException(status_code=404, detail=str(not_found_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while updating the coupon. Please try again later.",
            )


admin_coupon_api = AdminCouponApi()
admin_coupon_router = admin_coupon_api.router

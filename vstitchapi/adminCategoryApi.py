from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path

from vstitchDatabase.invalidReferenceError import InvalidReferenceError
from vstitchDatabase.uniqueConstraintError import UniqueConstraintError
from vstitchDTO.adminCategoryRequestDTO import CreateCategoryRequestDTO, UpdateCategoryRequestDTO
from vstitchDTO.adminCategoryResponseDTO import AdminCategoryResponseDTO
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.adminCategoryService import AdminCategoryService


class AdminCategoryApi:
    """Exposes the /admin/categories endpoints. Admin-JWT-gated at the
    router level, same mechanism as every other admin router.
    """

    def __init__(self):
        self.admin_category_service = AdminCategoryService()
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/categories",
            self.list_categories,
            methods=["GET"],
            response_model=List[AdminCategoryResponseDTO],
        )
        self.router.add_api_route(
            "/categories",
            self.create_category,
            methods=["POST"],
            response_model=AdminCategoryResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/categories/{vstitch_category_id}",
            self.update_category,
            methods=["PATCH"],
            response_model=AdminCategoryResponseDTO,
        )
        self.router.add_api_route(
            "/categories/{vstitch_category_id}",
            self.delete_category,
            methods=["DELETE"],
            status_code=204,
        )

    # Sync def - see orderapi.py's create_order for the full rationale.
    def list_categories(self):
        try:
            return self.admin_category_service.list_categories()
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading categories. Please try again later.",
            )

    def create_category(
        self,
        create_category_request_dto: CreateCategoryRequestDTO,
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.admin_category_service.create_category(
                create_category_request_dto, current_admin["admin_username"]
            )
        except UniqueConstraintError as conflict_error:
            raise HTTPException(status_code=409, detail=str(conflict_error))
        except InvalidReferenceError as invalid_reference_error:
            raise HTTPException(status_code=422, detail=str(invalid_reference_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while creating the category. Please try again later.",
            )

    def update_category(
        self,
        update_category_request_dto: UpdateCategoryRequestDTO,
        vstitch_category_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.admin_category_service.update_category(
                vstitch_category_id, update_category_request_dto, current_admin["admin_username"]
            )
        except UniqueConstraintError as conflict_error:
            raise HTTPException(status_code=409, detail=str(conflict_error))
        except InvalidReferenceError as invalid_reference_error:
            raise HTTPException(status_code=422, detail=str(invalid_reference_error))
        except ValueError as not_found_error:
            raise HTTPException(status_code=404, detail=str(not_found_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while updating the category. Please try again later.",
            )

    def delete_category(
        self,
        vstitch_category_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            self.admin_category_service.delete_category(vstitch_category_id, current_admin["admin_username"])
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while deleting the category. Please try again later.",
            )


admin_category_api = AdminCategoryApi()
admin_category_router = admin_category_api.router

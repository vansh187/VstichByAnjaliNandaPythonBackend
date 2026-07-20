from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from vstitchDatabase.invalidReferenceError import InvalidReferenceError
from vstitchDatabase.uniqueConstraintError import UniqueConstraintError
from vstitchDTO.adminProductRequestDTO import (
    CreateProductVariantRequestDTO,
    CreateProductsBatchRequestDTO,
    UpdateProductRequestDTO,
    UpdateProductVariantRequestDTO,
)
from vstitchDTO.adminProductResponseDTO import (
    AdminProductListResponseDTO,
    AdminProductResponseDTO,
    AdminProductVariantDTO,
    CreateProductsBatchResponseDTO,
)
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.adminProductService import AdminProductService


class AdminProductApi:
    """Exposes the /admin/products and /admin/product-variants endpoints.
    Admin-JWT-gated at the router level, same mechanism as every other
    admin router.
    """

    def __init__(self):
        self.admin_product_service = AdminProductService()
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/products", self.list_products, methods=["GET"], response_model=AdminProductListResponseDTO
        )
        self.router.add_api_route(
            "/products",
            self.create_products_batch,
            methods=["POST"],
            response_model=CreateProductsBatchResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/products/{vstitch_product_id}",
            self.update_product,
            methods=["PATCH"],
            response_model=AdminProductResponseDTO,
        )
        self.router.add_api_route(
            "/products/{vstitch_product_id}", self.delete_product, methods=["DELETE"], status_code=204
        )
        self.router.add_api_route(
            "/products/{vstitch_product_id}/variants",
            self.add_variant,
            methods=["POST"],
            response_model=AdminProductVariantDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/product-variants/{vstitch_product_variant_id}",
            self.update_variant,
            methods=["PATCH"],
            response_model=AdminProductVariantDTO,
        )
        self.router.add_api_route(
            "/product-variants/{vstitch_product_variant_id}",
            self.delete_variant,
            methods=["DELETE"],
            status_code=204,
        )

    # Sync def - see orderapi.py's create_order for the full rationale.
    def list_products(
        self,
        after_id: Optional[int] = Query(default=None, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        try:
            return self.admin_product_service.list_products(after_id, limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading products. Please try again later.",
            )

    def create_products_batch(
        self,
        create_products_batch_request_dto: CreateProductsBatchRequestDTO,
        current_admin: dict = Depends(get_current_admin),
    ):
        # No ValueError handling needed here: AdminProductService.create_products_batch
        # catches a per-product ValueError itself and reports it in the
        # response's errors[] - that's the whole point of the batch contract
        # (partial success, not all-or-nothing 4xx).
        try:
            return self.admin_product_service.create_products_batch(
                create_products_batch_request_dto, current_admin["admin_username"]
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while creating the products. Please try again later.",
            )

    def update_product(
        self,
        update_product_request_dto: UpdateProductRequestDTO,
        vstitch_product_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.admin_product_service.update_product(
                vstitch_product_id, update_product_request_dto, current_admin["admin_username"]
            )
        except InvalidReferenceError as invalid_reference_error:
            raise HTTPException(status_code=422, detail=str(invalid_reference_error))
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while updating the product. Please try again later.",
            )

    def delete_product(
        self,
        vstitch_product_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            self.admin_product_service.delete_product(vstitch_product_id, current_admin["admin_username"])
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while deleting the product. Please try again later.",
            )

    def add_variant(
        self,
        create_variant_request_dto: CreateProductVariantRequestDTO,
        vstitch_product_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.admin_product_service.add_variant(
                vstitch_product_id, create_variant_request_dto, current_admin["admin_username"]
            )
        except UniqueConstraintError as conflict_error:
            raise HTTPException(status_code=409, detail=str(conflict_error))
        except InvalidReferenceError as invalid_reference_error:
            raise HTTPException(status_code=422, detail=str(invalid_reference_error))
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while adding the variant. Please try again later.",
            )

    def update_variant(
        self,
        update_variant_request_dto: UpdateProductVariantRequestDTO,
        vstitch_product_variant_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.admin_product_service.update_variant(
                vstitch_product_variant_id, update_variant_request_dto, current_admin["admin_username"]
            )
        except UniqueConstraintError as conflict_error:
            raise HTTPException(status_code=409, detail=str(conflict_error))
        except InvalidReferenceError as invalid_reference_error:
            raise HTTPException(status_code=422, detail=str(invalid_reference_error))
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while updating the variant. Please try again later.",
            )

    def delete_variant(
        self,
        vstitch_product_variant_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            self.admin_product_service.delete_variant(vstitch_product_variant_id, current_admin["admin_username"])
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while deleting the variant. Please try again later.",
            )


admin_product_api = AdminProductApi()
admin_product_router = admin_product_api.router

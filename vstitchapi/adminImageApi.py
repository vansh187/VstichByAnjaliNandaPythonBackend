from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from vstitchDTO.adminImageResponseDTO import AdminImageUploadResponseDTO
from vstitchServices.adminAuditLogService import admin_audit_log_service
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.supabaseStorageService import SupabaseStorageService


class AdminImageApi:
    """Exposes POST /admin/images/upload - lets an admin upload a product or
    category photo directly instead of hosting it elsewhere first and
    pasting a URL in. Admin-JWT-gated at the router level, same mechanism
    as every other admin router. Returns only an image_url; POST
    /admin/products and POST /admin/categories are unchanged and still take
    that URL as a plain string field, so this is additive, not a breaking
    change to either contract.
    """

    def __init__(self):
        # Unlike GoogleAuthApi/RazorpayClient (whose __init__ preconditions
        # are satisfied by any placeholder string), SupabaseStorageService's
        # precondition is a DATABASE_URL that's actually a Supabase pooler
        # URL (postgres.<ref>@...) - CI's DATABASE_URL is a plain local
        # Postgres container instead, so eagerly constructing this at
        # `import main` time would fail CI the same way GOOGLE_CLIENT_ID
        # did before commit a848665, and no CI placeholder can fix it
        # without also breaking the real DB connection CI needs. Deferred
        # to first request instead - the module-level router still exists
        # eagerly (so `include_router` works), only this one dependency is lazy.
        self.supabase_storage_service = None
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/images/upload",
            self.upload_image,
            methods=["POST"],
            response_model=AdminImageUploadResponseDTO,
        )

    # Sync def - see orderapi.py's create_order for the full rationale.
    # file.file (the underlying SpooledTemporaryFile) is read synchronously
    # for the same reason, rather than via `await file.read()`.
    def upload_image(
        self,
        file: UploadFile = File(...),
        image_type: str = Form(...),
        current_admin: dict = Depends(get_current_admin),
    ):
        file_bytes = file.file.read()

        if self.supabase_storage_service is None:
            try:
                self.supabase_storage_service = SupabaseStorageService()
            except ValueError:
                # Misconfiguration (missing env vars), not a bad request -
                # a 500, unlike the client-input ValueErrors below.
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while uploading the image. Please try again later.",
                )

        try:
            image_url = self.supabase_storage_service.upload_image(file_bytes, file.content_type, image_type)
        except ValueError as validation_error:
            raise HTTPException(status_code=422, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while uploading the image. Please try again later.",
            )
        admin_audit_log_service.record(
            current_admin["vstitch_admin_id"], "upload_image", "image", None, {"image_type": image_type}
        )
        return AdminImageUploadResponseDTO(image_url=image_url)


admin_image_api = AdminImageApi()
admin_image_router = admin_image_api.router

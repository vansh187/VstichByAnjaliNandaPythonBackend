import io
import os
import re
import uuid

import requests
from PIL import Image

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
FOLDER_BY_IMAGE_TYPE = {"category": "categories", "product": "products"}
BUCKET_NAME = "VStitch-catalogue-images"
UPLOAD_REQUEST_TIMEOUT_SECONDS = 30
MAX_IMAGE_DIMENSION_PX = 1600
WEBP_QUALITY = 80


def compress_to_webp(file_bytes, max_dimension=MAX_IMAGE_DIMENSION_PX, quality=WEBP_QUALITY):
    """Shared by this service and scripts/reset_and_seed_catalog.py - a
    single source of truth for compression parameters, so the two can't
    silently drift (e.g. one call site's quality getting tuned without the
    other) the way a duplicated implementation would let them.
    """
    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image = image.convert("RGB")
            image.thumbnail((max_dimension, max_dimension))
            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=quality)
            return buffer.getvalue()
    except Exception as image_error:
        raise ValueError("The uploaded file is not a readable image.") from image_error


def _derive_supabase_url(database_url):
    # Mirrors scripts/reset_and_seed_catalog.py's derive_supabase_url - the
    # project's Storage REST base URL is taken from DATABASE_URL's own
    # embedded project ref (the "postgres.<ref>" pooler username) rather
    # than a separate SUPABASE_URL variable. .env has previously drifted so
    # SUPABASE_URL pointed at a different project than DATABASE_URL/the
    # service role key - DB queries kept working (they don't use
    # SUPABASE_URL) while every Storage call silently failed. Deriving it
    # from DATABASE_URL means the two can never disagree.
    match = re.search(r"//postgres\.([a-z0-9]+):", database_url)
    if not match:
        raise ValueError(
            "DATABASE_URL is not in the expected Supabase pooler format (postgres.<project-ref>@...)."
        )
    return f"https://{match.group(1)}.supabase.co"


class SupabaseStorageService:
    """Uploads admin-provided product/category images to Supabase Storage
    and returns the public URL - the only place this codebase talks to
    Storage directly, so callers (the upload endpoint) depend on this
    module's interface rather than Supabase's.

    Every uploaded image is converted to WebP and downsized (capped at
    MAX_IMAGE_DIMENSION_PX on the long edge) before upload - admin-supplied
    photos are typically much larger than the storefront needs, and
    shipping them as-is would slow every page that displays them.
    """

    def __init__(self):
        database_url = os.getenv("DATABASE_URL")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not database_url or not service_role_key:
            raise ValueError("DATABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not configured in the environment.")
        self.base_url = _derive_supabase_url(database_url)
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        }

    def upload_image(self, file_bytes, content_type, image_type):
        """Validates, compresses, and uploads one image. Raises ValueError
        (with a message safe to show the admin) on any validation failure
        or storage-backend error - callers translate that to a 422/500.
        """
        if image_type not in FOLDER_BY_IMAGE_TYPE:
            raise ValueError("image_type must be 'category' or 'product'.")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError("Only JPG, PNG, or WEBP images are allowed.")
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("Image must be smaller than 10MB.")

        webp_bytes = compress_to_webp(file_bytes)
        storage_path = f"{FOLDER_BY_IMAGE_TYPE[image_type]}/{uuid.uuid4().hex}.webp"
        self._upload_to_storage(storage_path, webp_bytes)
        return f"{self.base_url}/storage/v1/object/public/{BUCKET_NAME}/{storage_path}"

    def _upload_to_storage(self, storage_path, image_bytes):
        upload_headers = dict(self.headers)
        upload_headers["Content-Type"] = "image/webp"
        try:
            response = requests.post(
                f"{self.base_url}/storage/v1/object/{BUCKET_NAME}/{storage_path}",
                headers=upload_headers,
                data=image_bytes,
                timeout=UPLOAD_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as request_error:
            raise ValueError(f"Unable to upload image to storage: {request_error}") from request_error

from vstitchDatabase.categoryPersistence import CategoryPersistence
from vstitchDTO.adminCategoryResponseDTO import AdminCategoryResponseDTO
from vstitchServices.localCacheService import local_cache_service


class AdminCategoryService:
    """Business logic for the admin category-management endpoints."""

    def __init__(self):
        self.category_persistence = CategoryPersistence()

    def list_categories(self):
        rows = self.category_persistence.list_all_categories_admin()
        return [self._to_dto(row) for row in rows]

    def create_category(self, create_category_request_dto, admin_username):
        row = self.category_persistence.insert_category(
            create_category_request_dto.category_name,
            create_category_request_dto.parent_category_id,
            create_category_request_dto.image_url,
            f"admin:{admin_username}",
        )
        self._invalidate_cache()
        return self._to_dto(row)

    def update_category(self, vstitch_category_id, update_category_request_dto, admin_username):
        """Merges only the fields actually present on the request (per
        model_fields_set, not just non-None) onto the category's current
        row, then writes the full resolved row back - see
        UpdateCategoryRequestDTO's comment for why this can't just check
        "is the field None".
        """
        current = self.category_persistence.get_category_for_admin(vstitch_category_id)
        if current is None:
            raise ValueError(f"Category {vstitch_category_id} was not found.")

        supplied_fields = update_category_request_dto.model_fields_set
        category_name = (
            update_category_request_dto.category_name
            if "category_name" in supplied_fields
            else current["category_name"]
        )
        parent_category_id = (
            update_category_request_dto.parent_category_id
            if "parent_category_id" in supplied_fields
            else current["parent_category_id"]
        )
        image_url = (
            update_category_request_dto.image_url if "image_url" in supplied_fields else current["image_url"]
        )
        is_active = (
            update_category_request_dto.is_active if "is_active" in supplied_fields else current["is_active"]
        )

        row = self.category_persistence.update_category(
            vstitch_category_id, category_name, parent_category_id, image_url, is_active, f"admin:{admin_username}"
        )
        if row is None:
            raise ValueError(f"Category {vstitch_category_id} was not found.")
        self._invalidate_cache()
        return self._to_dto(row)

    def delete_category(self, vstitch_category_id, admin_username):
        """Soft-delete (IsActive=FALSE) - see soft_delete_category's
        comment in categoryPersistence.py for why this is never a real
        DELETE."""
        was_deleted = self.category_persistence.soft_delete_category(
            vstitch_category_id, f"admin:{admin_username}"
        )
        if not was_deleted:
            raise ValueError(f"Category {vstitch_category_id} was not found.")
        self._invalidate_cache()

    @staticmethod
    def _invalidate_cache():
        # Matches the existing precedent in orderService.py's stock-decrement
        # cache invalidation. Known limitation, not solved here: this cache
        # is in-process only (see localCacheService.py's own docstring) - a
        # write on one worker process won't invalidate another process's
        # cached copy until its TTL naturally expires.
        local_cache_service.delete("categories:list")

    @staticmethod
    def _to_dto(row):
        return AdminCategoryResponseDTO(
            vstitch_category_id=row["vstitch_category_id"],
            category_name=row["category_name"],
            parent_category_id=row["parent_category_id"],
            image_url=row["image_url"],
            is_active=row["is_active"],
        )

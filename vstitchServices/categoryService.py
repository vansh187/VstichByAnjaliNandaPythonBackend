from vstitchDatabase.categoryPersistence import CategoryPersistence
from vstitchDTO.categoryResponseDTO import CategoryResponseDTO
from vstitchServices.localCacheService import local_cache_service

CATEGORY_LIST_CACHE_KEY = "categories:list"
CATEGORY_LIST_CACHE_TTL_SECONDS = 120


class CategoryService:
    """Business logic for browsing the category tree."""

    def __init__(self):
        self.category_persistence = CategoryPersistence()

    def list_categories(self):
        cached_response = local_cache_service.get(CATEGORY_LIST_CACHE_KEY)
        if cached_response is not None:
            return cached_response

        rows = self.category_persistence.list_active_categories()
        response = [
            CategoryResponseDTO(
                vstitch_category_id=row["vstitch_category_id"],
                category_name=row["category_name"],
                parent_category_id=row["parent_category_id"],
            )
            for row in rows
        ]

        local_cache_service.set(CATEGORY_LIST_CACHE_KEY, response, CATEGORY_LIST_CACHE_TTL_SECONDS)
        return response

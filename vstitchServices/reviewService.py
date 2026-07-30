from vstitchDatabase.reviewPersistence import ReviewPersistence
from vstitchDTO.reviewResponseDTO import ReviewListItemDTO, ReviewListResponseDTO, ReviewResponseDTO


class ReviewService:
    """Business logic for submitting and browsing product reviews. No
    verified-purchase gating - any signed-in user may review any active
    product (a deliberate scope decision, not an oversight; can be layered
    on later without breaking this API's shape)."""

    def __init__(self):
        self.review_persistence = ReviewPersistence()

    def upsert_review(self, vstitch_product_id, vstitch_user_id, create_or_update_review_request_dto, actor):
        if not self.review_persistence.product_exists(vstitch_product_id):
            raise ValueError(f"Product {vstitch_product_id} was not found.")

        review_row, was_created = self.review_persistence.upsert_review(
            vstitch_user_id,
            vstitch_product_id,
            create_or_update_review_request_dto.rating,
            create_or_update_review_request_dto.review_text,
            actor,
        )
        return ReviewResponseDTO(**review_row), was_created

    def list_reviews_for_product(self, vstitch_product_id, before_id, limit):
        if not self.review_persistence.product_exists(vstitch_product_id):
            raise ValueError(f"Product {vstitch_product_id} was not found.")

        average_rating, review_count = self.review_persistence.get_review_stats_for_product(vstitch_product_id)
        rows = self.review_persistence.list_reviews_for_product(vstitch_product_id, before_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = page_rows[-1]["vstitch_review_id"] if has_more and page_rows else None

        return ReviewListResponseDTO(
            average_rating=average_rating,
            review_count=review_count,
            reviews=[ReviewListItemDTO(**row) for row in page_rows],
            has_more=has_more,
            next_cursor=next_cursor,
        )

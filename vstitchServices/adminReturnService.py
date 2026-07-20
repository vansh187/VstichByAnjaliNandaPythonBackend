from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchDTO.adminReturnResponseDTO import AdminReturnListResponseDTO, AdminReturnResponseDTO


class AdminReturnService:
    """Business logic for the admin returns-management endpoints."""

    def __init__(self):
        self.order_persistence = OrderPersistence()

    def list_returns(self, status, after_id, limit):
        rows = self.order_persistence.list_returns_for_admin(status, after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        returns = [AdminReturnResponseDTO(**row) for row in page_rows]
        next_cursor = page_rows[-1]["vstitch_return_order_id"] if has_more and page_rows else None
        return AdminReturnListResponseDTO(returns=returns, has_more=has_more, next_cursor=next_cursor)

    def update_return_status(self, vstitch_return_order_id, new_status, admin_username):
        row = self.order_persistence.update_return_status_admin(
            vstitch_return_order_id, new_status, f"admin:{admin_username}"
        )
        if row is None:
            raise ValueError(f"Return {vstitch_return_order_id} was not found.")
        return AdminReturnResponseDTO(**row)

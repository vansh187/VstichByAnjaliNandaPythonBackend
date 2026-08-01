import logging

from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchDTO.adminReturnResponseDTO import AdminReturnListResponseDTO, AdminReturnResponseDTO
from vstitchServices.paymentService import PaymentService

logger = logging.getLogger(__name__)

# Refund is triggered when a return/replace reaches this status - after the
# item has actually been picked up and verified, not the moment the customer
# first files the request (still just 'requested' at that point).
REFUND_TRIGGER_STATUS = "completed"


class AdminReturnService:
    """Business logic for the admin returns-management endpoints."""

    def __init__(self):
        self.order_persistence = OrderPersistence()

    def list_returns(self, status, request_type, after_id, limit):
        rows = self.order_persistence.list_returns_for_admin(status, request_type, after_id, limit + 1)
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

        refund_triggered = None
        if new_status == REFUND_TRIGGER_STATUS:
            refund_triggered = self._try_trigger_refund(row, admin_username)

        return AdminReturnResponseDTO(**row, refund_triggered=refund_triggered)

    def _try_trigger_refund(self, return_row, admin_username):
        """Attempts to refund the order's captured payment now that its
        return/replace is 'completed'. Deliberately never lets a refund
        failure raise back out of update_return_status - the admin's status
        update has already succeeded and must stay succeeded; a refund
        problem (no captured payment, Razorpay error, etc.) is surfaced only
        via the returned refund_triggered=False for ops to retry manually,
        never as a failed API call for an update that did, in fact, apply.
        """
        try:
            PaymentService().refund_order_payment(
                return_row["vstitch_order_id"],
                reason=f"Return #{return_row['vstitch_return_order_id']} completed",
                updated_by=f"admin:{admin_username}",
            )
            return True
        except Exception:
            logger.exception(
                "Refund trigger failed for return %s (order %s) after marking it completed - status update "
                "itself succeeded; refund needs manual retry.",
                return_row["vstitch_return_order_id"],
                return_row["vstitch_order_id"],
            )
            return False

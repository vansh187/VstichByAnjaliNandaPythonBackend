from datetime import date

from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchDatabase.productPersistence import ProductPersistence
from vstitchDTO.adminRevenueResponseDTO import RevenueDailyItemDTO, RevenueSummaryResponseDTO

# Active variants at or below this stock level count as "low stock" on the
# dashboard - a plain constant so it's a one-line change if the threshold
# ever needs to move.
LOW_STOCK_THRESHOLD = 5


class AdminRevenueService:
    """Business logic for the admin revenue/dashboard endpoints."""

    def __init__(self):
        self.order_persistence = OrderPersistence()
        self.product_persistence = ProductPersistence()

    def get_summary(self, from_date, to_date):
        """today_revenue/today_orders_count are scoped to [from_date, to_date]
        (both default to today at the API layer); total_revenue/
        total_orders_count are all-time, unfiltered - see the two separate
        calls below.
        """
        today_revenue, today_orders_count = self.order_persistence.get_revenue_for_period(from_date, to_date)
        total_revenue, total_orders_count = self.order_persistence.get_revenue_for_period(None, None)

        return RevenueSummaryResponseDTO(
            today_revenue=today_revenue,
            today_orders_count=today_orders_count,
            total_revenue=total_revenue,
            total_orders_count=total_orders_count,
            pending_orders_count=self.order_persistence.count_pending_orders(),
            low_stock_count=self.product_persistence.count_low_stock_variants(LOW_STOCK_THRESHOLD),
            pending_shipments_count=self.order_persistence.count_pending_shipments(),
        )

    def get_daily(self, from_date, to_date):
        rows = self.order_persistence.get_revenue_daily(from_date, to_date)
        return [RevenueDailyItemDTO(date=row[0], revenue=row[1], orders_count=row[2]) for row in rows]

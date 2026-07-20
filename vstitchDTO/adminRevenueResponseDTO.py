from datetime import date
from typing import List

from pydantic import BaseModel


class RevenueSummaryResponseDTO(BaseModel):
    today_revenue: float
    today_orders_count: int
    total_revenue: float
    total_orders_count: int
    pending_orders_count: int
    low_stock_count: int
    pending_shipments_count: int


class RevenueDailyItemDTO(BaseModel):
    date: date
    revenue: float
    orders_count: int

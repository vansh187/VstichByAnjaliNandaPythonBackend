from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from vstitchDTO.adminRevenueResponseDTO import RevenueDailyItemDTO, RevenueSummaryResponseDTO
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.adminRevenueService import AdminRevenueService


class AdminRevenueApi:
    """Exposes the /admin/revenue endpoints - dashboard summary and daily
    trend. Admin-JWT-gated at the router level, same mechanism as every
    other admin router.
    """

    def __init__(self):
        self.admin_revenue_service = AdminRevenueService()
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/revenue/summary",
            self.get_summary,
            methods=["GET"],
            response_model=RevenueSummaryResponseDTO,
        )
        self.router.add_api_route(
            "/revenue/daily",
            self.get_daily,
            methods=["GET"],
            response_model=List[RevenueDailyItemDTO],
        )

    # Sync def - see orderapi.py's create_order for the full rationale
    # (psycopg2 is blocking; FastAPI dispatches sync handlers to its
    # worker-thread pool).
    def get_summary(
        self,
        from_date: Optional[date] = Query(default=None),
        to_date: Optional[date] = Query(default=None),
    ):
        try:
            return self.admin_revenue_service.get_summary(
                from_date or date.today(), to_date or date.today()
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading the revenue summary. Please try again later.",
            )

    def get_daily(
        self,
        from_date: Optional[date] = Query(default=None),
        to_date: Optional[date] = Query(default=None),
    ):
        try:
            return self.admin_revenue_service.get_daily(
                from_date or date.today(), to_date or date.today()
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading the revenue trend. Please try again later.",
            )


admin_revenue_api = AdminRevenueApi()
admin_revenue_router = admin_revenue_api.router

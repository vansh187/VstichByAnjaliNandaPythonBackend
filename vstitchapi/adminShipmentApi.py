from vstitchapi.shipmentRouterFactory import build_shipment_router
from vstitchServices.adminAuthDependency import get_current_admin

# Admin-facing mirror of shipmentOpsApi.py's fulfillment endpoints - AWB
# assignment, pickup/label/manifest/invoice generation, NDR. Gated by an
# admin bearer token instead of the internal ops API key.
#
# Deliberately not an HTTP proxy that constructs and forwards the ops key:
# shipmentOpsApi.py's own handlers call ShipmentService() methods
# in-process (the ops key is a FastAPI dependency on that router, not
# something ShipmentService itself needs), so this router calls the exact
# same ShipmentService methods directly via the shared
# shipmentRouterFactory.py builder. The admin panel (a browser app) never
# holds, sees, or sends the internal ops key at all - stronger than the
# "inject it server-side" ask, since it's never in play here either.
admin_shipment_router = build_shipment_router("/admin/shipments", get_current_admin)

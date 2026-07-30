from vstitchapi.shipmentRouterFactory import build_shipment_router
from vstitchServices.internalOpsAuthDependency import require_internal_ops_key

# Internal fulfillment/warehouse endpoints - AWB assignment, pickup/label/
# manifest/invoice generation, NDR. Not for the public frontend team: gated
# by a shared internal API key (see internalOpsAuthDependency.py) rather
# than a customer JWT, since this codebase has no admin/staff role to gate
# on yet. See adminShipmentApi.py for the JWT-gated admin-panel mirror of
# this same route set - both are built from shipmentRouterFactory.py so the
# two proxies can't silently drift from each other.
shipment_ops_router = build_shipment_router("/ops/shipments", require_internal_ops_key)

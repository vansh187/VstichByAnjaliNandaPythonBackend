from fastapi import APIRouter, Depends, HTTPException, Path

from vstitchDTO.shipmentRequestDTO import NdrActionRequestDTO, ShipmentBatchRequestDTO
from vstitchServices.internalOpsAuthDependency import require_internal_ops_key
from vstitchServices.shipmentService import ShipmentService


class ShipmentOpsApi:
    """Internal fulfillment/warehouse endpoints - AWB assignment, pickup/
    label/manifest/invoice generation, NDR. Not for the public frontend team:
    gated by a shared internal API key (see internalOpsAuthDependency.py)
    rather than a customer JWT, since this codebase has no admin/staff role
    to gate on yet.
    """

    def __init__(self):
        self.router = APIRouter(
            prefix="/ops/shipments",
            dependencies=[Depends(require_internal_ops_key)],
        )
        self.router.add_api_route("/{vstitch_order_id}/awb", self.assign_awb, methods=["POST"])
        self.router.add_api_route("/pickup", self.generate_pickup, methods=["POST"])
        self.router.add_api_route("/label", self.generate_label, methods=["POST"])
        self.router.add_api_route("/manifest", self.generate_manifest, methods=["POST"])
        self.router.add_api_route("/invoice", self.generate_invoice, methods=["POST"])
        self.router.add_api_route("/ndr", self.get_ndr_orders, methods=["GET"])
        self.router.add_api_route("/ndr/action", self.take_ndr_action, methods=["POST"])

    def assign_awb(self, vstitch_order_id: int = Path(..., ge=1)):
        try:
            return ShipmentService().assign_awb_for_order(vstitch_order_id)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong assigning a courier/AWB.")

    def generate_pickup(self, batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_pickup_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating pickup.")

    def generate_label(self, batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_label_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating the label.")

    def generate_manifest(self, batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_manifest_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating the manifest.")

    def generate_invoice(self, batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_invoice_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating the invoice.")

    def get_ndr_orders(self):
        try:
            return ShipmentService().get_ndr_orders()
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong fetching NDR orders.")

    def take_ndr_action(self, ndr_action_request_dto: NdrActionRequestDTO):
        try:
            return ShipmentService().take_ndr_action(ndr_action_request_dto.ndr_action_payload)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong taking the NDR action.")


shipment_ops_api = ShipmentOpsApi()
shipment_ops_router = shipment_ops_api.router

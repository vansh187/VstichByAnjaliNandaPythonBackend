from fastapi import APIRouter, Depends, HTTPException, Path

from vstitchDTO.shipmentRequestDTO import NdrActionRequestDTO, ShipmentBatchRequestDTO
from vstitchServices.shipmentService import ShipmentService


def build_shipment_router(prefix, auth_dependency):
    """Builds the 7 shipment-fulfillment routes (AWB assignment, pickup/
    label/manifest/invoice generation, NDR) shared by shipmentOpsApi.py (the
    internal ops-key proxy) and adminShipmentApi.py (the admin-JWT proxy) -
    same ShipmentService calls and error mapping either way, the only
    difference being which auth dependency gates the router and which URL
    prefix it's mounted under. Kept as one shared implementation so a change
    to one route's behavior can't be applied to only one of the two proxies
    by accident.
    """
    router = APIRouter(prefix=prefix, dependencies=[Depends(auth_dependency)])

    def assign_awb(vstitch_order_id: int = Path(..., ge=1)):
        try:
            return ShipmentService().assign_awb_for_order(vstitch_order_id)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong assigning a courier/AWB.")

    def generate_pickup(batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_pickup_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating pickup.")

    def generate_label(batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_label_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating the label.")

    def generate_manifest(batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_manifest_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating the manifest.")

    def generate_invoice(batch: ShipmentBatchRequestDTO):
        try:
            return ShipmentService().generate_invoice_for_orders(batch.vstitch_order_ids)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong generating the invoice.")

    def get_ndr_orders():
        try:
            return ShipmentService().get_ndr_orders()
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong fetching NDR orders.")

    def take_ndr_action(ndr_action_request_dto: NdrActionRequestDTO):
        try:
            return ShipmentService().take_ndr_action(ndr_action_request_dto.ndr_action_payload)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(status_code=502, detail="Something went wrong taking the NDR action.")

    router.add_api_route("/{vstitch_order_id}/awb", assign_awb, methods=["POST"])
    router.add_api_route("/pickup", generate_pickup, methods=["POST"])
    router.add_api_route("/label", generate_label, methods=["POST"])
    router.add_api_route("/manifest", generate_manifest, methods=["POST"])
    router.add_api_route("/invoice", generate_invoice, methods=["POST"])
    router.add_api_route("/ndr", get_ndr_orders, methods=["GET"])
    router.add_api_route("/ndr/action", take_ndr_action, methods=["POST"])

    return router

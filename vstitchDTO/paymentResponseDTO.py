from pydantic import BaseModel


class CreatePaymentOrderResponseDTO(BaseModel):
    """Everything the frontend needs to hand straight to Razorpay Checkout.js
    (new Razorpay({...}).open()) without a second round trip - vstitch_order_id
    is the only field that isn't a direct Checkout.js option, kept for the
    frontend to correlate the payment back to the order it just placed.
    """

    vstitch_order_id: int
    razorpay_order_id: str
    razorpay_key_id: str
    amount: int
    currency: str

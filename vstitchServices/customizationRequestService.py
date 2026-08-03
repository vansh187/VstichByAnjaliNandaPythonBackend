from vstitchDatabase.customizationRequestPersistence import CustomizationRequestPersistence

# created_by records the submission channel, not "who" - VstitchUserId is
# already the single source of truth for that (NULL for an anonymous
# shopper, a real id otherwise), matching how other tables use created_by
# for a source label (e.g. "shiprocket-webhook", "customer-return-request")
# rather than duplicating an id that's already a column on the same row.
CUSTOMIZATION_REQUEST_SOURCE = "storefront"


class CustomizationRequestService:
    """Business logic for the "Request bespoke measurements" product-page
    form: validates the product/variant pair the shopper was looking at,
    then persists the request - anonymously if no bearer token was sent,
    attached to the user otherwise.
    """

    def __init__(self):
        self.customization_request_persistence = CustomizationRequestPersistence()

    def create_request(self, vstitch_product_id, vstitch_product_variant_id, request_dto, vstitch_user_id):
        """Raises ValueError (-> 404 at the API layer) if vstitch_product_id/
        vstitch_product_variant_id don't exist or don't belong to each other -
        every one of those is reported identically ("not found"), never
        distinguished, so a caller probing ids can't tell which half of the
        pair was wrong.
        """
        variant_exists = self.customization_request_persistence.variant_belongs_to_product(
            vstitch_product_id, vstitch_product_variant_id
        )
        if not variant_exists:
            raise ValueError(f"Product {vstitch_product_id} / variant {vstitch_product_variant_id} was not found.")

        return self.customization_request_persistence.create_customization_request(
            vstitch_product_id,
            vstitch_product_variant_id,
            vstitch_user_id,
            request_dto.customer_name,
            request_dto.customer_phone,
            request_dto.bust_in,
            request_dto.waist_in,
            request_dto.hips_in,
            request_dto.shoulder_in,
            request_dto.sleeve_length_in,
            request_dto.dress_length_in,
            request_dto.notes,
            CUSTOMIZATION_REQUEST_SOURCE,
        )

    def list_requests_for_user(self, vstitch_user_id):
        return self.customization_request_persistence.get_requests_for_user(vstitch_user_id)

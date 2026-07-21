# Add Product Form — Missing Fields (Frontend Action Doc)

Audience: frontend team refactoring the admin "Add Products" modal.
Full API contract: see `ADMIN_API_REFERENCE.md` → **Products** section
(`POST /admin/products`). This doc only calls out the gap between what
that API accepts and what the current form sends.

## TL;DR

The backend already accepts and stores `description` and all four
shipping dimensions (`weight_kg`, `length_cm`, `breadth_cm`, `height_cm`)
per variant, plus a full `images[]` array. **The current modal has no
inputs for any of these**, so every product created through it ships with
them `NULL`/empty. This is a UI gap, not a backend gap — no API changes
are needed to fix it.

Live proof: product `vstitch_product_id = 16` ("Duppatta white
customized"), created through the current admin panel today
(2026-07-20), has:
- `description = NULL`
- variant `weight_kg / length_cm / breadth_cm / height_cm` all `NULL`
- **zero rows** in `VStitch_ProductImages` (no photos at all)

The dimension gap isn't cosmetic: an order containing this product
**cannot get a Shiprocket shipment created** until an admin backfills
those four fields via `PATCH /admin/product-variants/{id}`, because
shipment creation hard-requires them.

## Fields to add to the form

| Field | Belongs to | Request key | Type | Required? |
|---|---|---|---|---|
| Description | Product (once per product) | `description` | string | Optional, but should be a normal textarea — currently has no input at all |
| Weight (kg) | Per variant/row | `weight_kg` | number | Optional at creation; **required before the product can ship** |
| Length (cm) | Per variant/row | `length_cm` | number | Same as above |
| Breadth (cm) | Per variant/row | `breadth_cm` | number | Same as above |
| Height (cm) | Per variant/row | `height_cm` | number | Same as above |
| Image(s) | Per product | `images: [{ image_url, is_primary, display_order }]` | array | Optional, but a product with zero images has no photo on the storefront (product 16 is a live example) |

Validation rules already enforced server-side (mirror them client-side so
the admin gets instant feedback instead of a 422 round-trip):
- `weight_kg`, if provided, must be `> 0`.
- `length_cm` / `breadth_cm` / `height_cm`, if provided, must each be `>= 0.5`.
- All four are optional as a set — an admin can save a product without
  them, but the form should visually flag "shipping info incomplete" so
  it doesn't get forgotten (that's exactly what happened with product 16).

## Suggested form layout change

Add to the existing per-variant card (next to Size/Color/Price/Stock):
```
Weight (kg)   Length (cm)   Breadth (cm)   Height (cm)
[        ]    [         ]   [          ]   [         ]
```

Add above/below the variant list (once per product, not per variant):
```
Description
[ textarea, multi-line ]

Images
[ + Add image URL ]   (repeatable: image_url, is_primary toggle, display_order)
```

## Request shape reference (copy-paste for the frontend's API client)

```json
POST /admin/products
{
  "products": [
    {
      "product_name": "Duppatta white customized",
      "description": "Hand-embroidered white duppatta, customizable.",
      "category_id": 9,
      "base_price": 897.00,
      "is_active": true,
      "variants": [
        {
          "sku": "SAR-0162",
          "size": "Standard",
          "color": "Standard",
          "price": 897.00,
          "stock_quantity": 3,
          "weight_kg": 0.25,
          "length_cm": 40.0,
          "breadth_cm": 30.0,
          "height_cm": 2.0
        }
      ],
      "images": [
        { "image_url": "https://storage.example.com/products/dup-white.jpg", "is_primary": true, "display_order": 0 }
      ]
    }
  ]
}
```

## One known backend limitation (not a blocker, flagging for awareness)

Images are always attached at the **product** level — there's currently
no way to tag an uploaded image to one specific variant/color (e.g. if a
saree comes in red and blue, you can't say "this photo is the red one").
The `VStitch_ProductImages` table has a `VstitchProductVariantId` column
for exactly this, but the create/insert code never populates it. Not
needed to fix the immediate "missing fields" problem above — call it out
separately if the catalog UI needs per-color photos later.

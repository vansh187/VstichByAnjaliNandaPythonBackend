import html

BRAND_NAME = "VStitch by Anjali Nanda"
BRAND_COLOR = "#7A2E3B"
LIGHT_BG_COLOR = "#F6EDEF"
BORDER_COLOR = "#E3D3D7"
TEXT_COLOR = "#3A2E31"
MUTED_TEXT_COLOR = "#7A6C6F"

# Every string interpolated into the HTML below came from user input at some
# point (checkout form, product name, notes) - these templates are built by
# hand with f-strings, not a templating engine with auto-escaping, so _esc
# is applied at every single interpolation site. Skipping it anywhere here
# would let a customer's own name/address/notes inject markup into an email
# rendered in Resend's/the recipient's mail client.
def _esc(value):
    return html.escape(str(value)) if value is not None else ""


def _format_currency(amount):
    return f"Rs. {float(amount):,.2f}"


def _format_date(created_date):
    return created_date.strftime("%d %b %Y, %I:%M %p") if created_date else "-"


def _shipping_address_html(order):
    address_lines = [order["shipping_address_line1"]]
    if order["shipping_address_line2"]:
        address_lines.append(order["shipping_address_line2"])
    address_lines.append(f"{order['shipping_city']}, {order['shipping_state']} {order['shipping_postal_code']}")
    address_lines.append(order["shipping_country"])
    return "<br/>".join(_esc(line) for line in address_lines)


def _email_shell(preheader, body_html):
    """Shared wrapper (header bar + footer) both emails render inside -
    table-based layout with inline styles throughout, since email clients
    don't reliably support external/embedded stylesheets, flexbox, or grid.
    """
    return f"""\
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{_esc(BRAND_NAME)}</title>
  </head>
  <body style="margin:0; padding:0; background-color:#F3EEEF; font-family:Helvetica,Arial,sans-serif; color:{TEXT_COLOR};">
    <div style="display:none; max-height:0; overflow:hidden;">{_esc(preheader)}</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F3EEEF; padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF; border-radius:8px; overflow:hidden; max-width:600px; width:100%;">
            <tr>
              <td style="background-color:{BRAND_COLOR}; padding:24px 32px;">
                <span style="font-size:20px; font-weight:bold; color:#FFFFFF; letter-spacing:0.5px;">{_esc(BRAND_NAME)}</span>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                {body_html}
              </td>
            </tr>
            <tr>
              <td style="background-color:{LIGHT_BG_COLOR}; padding:20px 32px; font-size:12px; color:{MUTED_TEXT_COLOR};">
                &copy; {_esc(BRAND_NAME)}. This is an automated message - please do not mark as spam if you recently placed an order.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _items_table_html(order):
    rows = []
    for item in order["items"]:
        line_total = float(item["unit_price"]) * item["quantity"]
        rows.append(
            f"""
            <tr>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:14px;">
                {_esc(item['product_name'])}<br/>
                <span style="font-size:12px; color:{MUTED_TEXT_COLOR};">
                  {_esc(item['size'] or '-')} / {_esc(item['color'] or '-')}
                </span>
              </td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:14px; text-align:center;">{item['quantity']}</td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:14px; text-align:right;">{_esc(_format_currency(line_total))}</td>
            </tr>"""
        )
    return "".join(rows)


def build_customer_confirmation_email(order):
    """Returns (subject, html_body) for the order-confirmation email sent to
    the customer whose order was just placed (COD) or paid for (Razorpay
    capture). The PDF invoice is attached separately by the caller - this
    only builds the email body.
    """
    order_id = order["vstitch_order_id"]
    subject = f"Order Confirmed - #{order_id} | {BRAND_NAME}"

    payment_note = (
        "Payment received - your order is confirmed."
        if order["payment_method"] == "razorpay"
        else "Cash on Delivery - pay when your order arrives."
    )

    body_html = f"""
    <h1 style="font-size:20px; margin:0 0 8px 0; color:{TEXT_COLOR};">Thank you for your order!</h1>
    <p style="font-size:14px; line-height:1.6; margin:0 0 20px 0; color:{TEXT_COLOR};">
      Hi {_esc(order['shipping_recipient_name'])}, we've received your order and it's being prepared for
      dispatch. {_esc(payment_note)} A detailed invoice is attached to this email as a PDF for your records.
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{LIGHT_BG_COLOR}; border-radius:6px; margin-bottom:24px;">
      <tr>
        <td style="padding:16px 20px; font-size:13px; color:{MUTED_TEXT_COLOR};">
          Order Number<br/><span style="font-size:16px; font-weight:bold; color:{TEXT_COLOR};">#{order_id}</span>
        </td>
        <td style="padding:16px 20px; font-size:13px; color:{MUTED_TEXT_COLOR};">
          Order Date<br/><span style="font-size:14px; color:{TEXT_COLOR};">{_esc(_format_date(order['created_date']))}</span>
        </td>
      </tr>
    </table>

    <h2 style="font-size:15px; margin:0 0 12px 0; color:{BRAND_COLOR};">Order Summary</h2>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; margin-bottom:8px;">
      <tr>
        <th style="text-align:left; padding:8px; font-size:12px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">ITEM</th>
        <th style="text-align:center; padding:8px; font-size:12px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">QTY</th>
        <th style="text-align:right; padding:8px; font-size:12px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">AMOUNT</th>
      </tr>
      {_items_table_html(order)}
      <tr>
        <td colspan="2" style="padding:12px 8px; font-size:15px; font-weight:bold; text-align:right;">Total</td>
        <td style="padding:12px 8px; font-size:15px; font-weight:bold; text-align:right;">{_esc(_format_currency(order['total_amount']))}</td>
      </tr>
    </table>

    <h2 style="font-size:15px; margin:24px 0 8px 0; color:{BRAND_COLOR};">Shipping To</h2>
    <p style="font-size:14px; line-height:1.6; margin:0 0 4px 0;">{_esc(order['shipping_recipient_name'])}</p>
    <p style="font-size:14px; line-height:1.6; margin:0 0 4px 0; color:{MUTED_TEXT_COLOR};">{_shipping_address_html(order)}</p>
    <p style="font-size:14px; line-height:1.6; margin:0 0 24px 0; color:{MUTED_TEXT_COLOR};">Phone: {_esc(order['shipping_phone_number'])}</p>

    <p style="font-size:13px; line-height:1.6; color:{MUTED_TEXT_COLOR}; margin:0;">
      Questions about your order? Just reply to this email and our team will help you out.
    </p>
    """

    preheader = f"Your order #{order_id} with {BRAND_NAME} is confirmed."
    return subject, _email_shell(preheader, body_html)


def build_admin_notification_email(order):
    """Returns (subject, html_body) for the internal "prepare for delivery"
    email sent to the studio's fulfillment inbox. Every line item lists its
    VstitchProductId/VstitchProductVariantId/SKU explicitly - per spec, this
    is what lets staff identify and pack the exact item from the email
    alone, without needing to cross-reference the admin dashboard first.
    """
    order_id = order["vstitch_order_id"]
    subject = f"New Order #{order_id} - Prepare for Delivery"

    item_rows = []
    for item in order["items"]:
        line_total = float(item["unit_price"]) * item["quantity"]
        product_id_display = item["vstitch_product_id"] if item["vstitch_product_id"] is not None else "N/A"
        variant_id_display = (
            item["vstitch_product_variant_id"] if item["vstitch_product_variant_id"] is not None else "N/A"
        )
        sku_display = item["sku"] or "N/A"
        item_rows.append(
            f"""
            <tr>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:13px;">{_esc(item['product_name'])}</td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:13px;">{_esc(product_id_display)}</td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:13px;">{_esc(variant_id_display)}</td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:13px;">{_esc(sku_display)}</td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:13px;">{_esc(item['size'] or '-')} / {_esc(item['color'] or '-')}</td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:13px; text-align:center;">{item['quantity']}</td>
              <td style="padding:10px 8px; border-bottom:1px solid {BORDER_COLOR}; font-size:13px; text-align:right;">{_esc(_format_currency(line_total))}</td>
            </tr>"""
        )

    payment_note = "PAID (Razorpay)" if order["payment_method"] == "razorpay" else "COD - collect cash on delivery"

    body_html = f"""
    <h1 style="font-size:20px; margin:0 0 8px 0; color:{TEXT_COLOR};">New order received - please prepare for delivery</h1>
    <p style="font-size:14px; line-height:1.6; margin:0 0 20px 0; color:{TEXT_COLOR};">
      Order <b>#{order_id}</b> was placed on {_esc(_format_date(order['created_date']))}. Payment status:
      <b>{_esc(payment_note)}</b>. Please pack the items below and hand off for shipment.
    </p>

    <h2 style="font-size:15px; margin:0 0 12px 0; color:{BRAND_COLOR};">Items to Pack</h2>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; margin-bottom:8px;">
      <tr>
        <th style="text-align:left; padding:8px; font-size:11px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">PRODUCT</th>
        <th style="text-align:left; padding:8px; font-size:11px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">PRODUCT ID</th>
        <th style="text-align:left; padding:8px; font-size:11px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">VARIANT ID</th>
        <th style="text-align:left; padding:8px; font-size:11px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">SKU</th>
        <th style="text-align:left; padding:8px; font-size:11px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">SIZE / COLOR</th>
        <th style="text-align:center; padding:8px; font-size:11px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">QTY</th>
        <th style="text-align:right; padding:8px; font-size:11px; color:{MUTED_TEXT_COLOR}; border-bottom:2px solid {BRAND_COLOR};">AMOUNT</th>
      </tr>
      {"".join(item_rows)}
      <tr>
        <td colspan="6" style="padding:12px 8px; font-size:14px; font-weight:bold; text-align:right;">Order Total</td>
        <td style="padding:12px 8px; font-size:14px; font-weight:bold; text-align:right;">{_esc(_format_currency(order['total_amount']))}</td>
      </tr>
    </table>

    <h2 style="font-size:15px; margin:24px 0 8px 0; color:{BRAND_COLOR};">Ship To</h2>
    <p style="font-size:14px; line-height:1.6; margin:0 0 4px 0;">{_esc(order['shipping_recipient_name'])}</p>
    <p style="font-size:14px; line-height:1.6; margin:0 0 4px 0; color:{MUTED_TEXT_COLOR};">{_shipping_address_html(order)}</p>
    <p style="font-size:14px; line-height:1.6; margin:0; color:{MUTED_TEXT_COLOR};">Phone: {_esc(order['shipping_phone_number'])}</p>
    """

    preheader = f"Order #{order_id} needs to be packed and prepared for delivery."
    return subject, _email_shell(preheader, body_html)

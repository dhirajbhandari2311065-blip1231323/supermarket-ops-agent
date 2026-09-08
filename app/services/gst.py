from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict


class TaxBreakup(TypedDict):
    subtotal: Decimal
    gst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal


def calculate_item_gst(unit_price: Decimal, quantity: Decimal, gst_rate: Decimal) -> TaxBreakup:
    """
    Computes subtotal, CGST, SGST, and grand total using exact Decimal arithmetic.
    Rounds currency values to 2 decimal places using ROUND_HALF_UP.
    """
    # Force Decimal conversion
    unit_price = Decimal(str(unit_price))
    quantity = Decimal(str(quantity))
    gst_rate = Decimal(str(gst_rate))

    subtotal = (unit_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    total_tax = (subtotal * (gst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Intra-state split: 50% CGST, 50% SGST
    cgst_amount = (total_tax / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sgst_amount = total_tax - cgst_amount  # Avoid precision loss rounding errors
    
    grand_total = subtotal + total_tax

    return {
        "subtotal": subtotal,
        "gst_rate": gst_rate,
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
        "total_tax": total_tax,
        "grand_total": grand_total,
    }
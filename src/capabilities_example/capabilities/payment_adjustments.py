from __future__ import annotations

from pydantic_ai.capabilities import Capability

payment_adjustments = Capability(
    id="payment-adjustments",
    description=(
        "Use for payment corrections related to refunds: duplicate charges, price "
        "adjustments, tax corrections, shipping fee reversals, split tenders, gift cards, "
        "store credit, and chargeback-sensitive cases."
    ),
    instructions=(
        "Separate true refunds from payment adjustments. A duplicate authorization may "
        "expire without a refund. A captured duplicate payment needs a refund case. A price "
        "match can be handled as a partial refund or store credit depending on policy. "
        "When a customer paid with multiple tenders, explain that each tender may receive "
        "a separate credit. Avoid processing merchant-initiated refunds for active "
        "chargebacks; collect details and escalate to payments risk."
    ),
    defer_loading=True,
)


@payment_adjustments.tool_plain
def payment_tenders(order_id: str) -> str:
    """Look up payment tenders used by an order."""
    return (
        f"Order {order_id}: paid with Visa ending 4242 for $72.40 and store credit "
        "for $15.00."
    )


@payment_adjustments.tool_plain
def calculate_adjustment(order_id: str, adjustment_type: str) -> str:
    """Calculate the amount and destination for a payment adjustment."""
    return (
        f"Order {order_id}: {adjustment_type} adjustment calculated as $9.99. "
        "Return $7.99 to original card and $2.00 to store credit."
    )

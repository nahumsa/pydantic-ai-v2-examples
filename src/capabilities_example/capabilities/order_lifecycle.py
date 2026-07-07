from __future__ import annotations

from pydantic_ai.capabilities import Capability

order_lifecycle = Capability(
    id="order-lifecycle",
    description=(
        "Use before refund work when the user asks about order status, delivery state, "
        "cancellation state, fulfillment progress, or whether an order can still be changed."
    ),
    instructions=(
        "Treat order lifecycle as the source of truth before discussing refund outcomes. "
        "Confirm the order ID and distinguish pending authorization, paid, packed, shipped, "
        "delivered, cancelled, failed delivery, and returned states. If an order is already "
        "shipped, do not offer cancellation as a refund path; explain return or carrier "
        "intercept options. If an order was cancelled before capture, describe it as a "
        "voided authorization rather than a refund. If fulfillment is partial, separate "
        "refundable line items from line items still in transit."
    ),
    defer_loading=True,
)


@order_lifecycle.tool_plain
def order_status(order_id: str) -> str:
    """Look up the fulfillment and delivery status for an order."""
    return (
        f"Order {order_id}: delivered on 2026-04-28; two items fulfilled, "
        "one item returned to sender."
    )


@order_lifecycle.tool_plain
def cancellation_window(order_id: str) -> str:
    """Check whether an order can be cancelled before refund or return handling."""
    return (
        f"Order {order_id}: cancellation window closed because the shipment is delivered. "
        "Use return or refund workflows instead."
    )

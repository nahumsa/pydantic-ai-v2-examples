from __future__ import annotations

from pydantic_ai.capabilities import Capability

return_shipping = Capability(
    id="return-shipping",
    description=(
        "Use when refund eligibility depends on returning merchandise, return labels, "
        "carrier pickup, drop-off instructions, return tracking, inspection, or restocking fees."
    ),
    instructions=(
        "Before promising a refund for physical goods, determine whether the item must be "
        "returned and whether return shipping is prepaid. Provide label, package, drop-off, "
        "and tracking guidance when the customer needs to send goods back. Explain that "
        "inspection can change the final refund when items are damaged, missing accessories, "
        "outside the return window, or subject to restocking fees. If the merchant caused "
        "the issue, do not apply customer-paid return shipping in the response."
    ),
    defer_loading=True,
)


@return_shipping.tool_plain
def return_label(order_id: str) -> str:
    """Create or retrieve a return shipping label for an order."""
    return (
        f"Order {order_id}: prepaid return label RL-{order_id[-4:]} is active; "
        "carrier drop-off deadline is 2026-05-15."
    )


@return_shipping.tool_plain
def return_tracking(order_id: str) -> str:
    """Look up return shipment tracking and inspection status."""
    return (
        f"Order {order_id}: return package received on 2026-05-03; inspection pending."
    )

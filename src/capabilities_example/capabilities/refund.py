from pydantic_ai.capabilities import Capability

refunds = Capability(
    id="refunds",
    description=(
        "Use for refund eligibility, refund status, refund timing, refund method, "
        "or processing a monetary refund for a customer order."
    ),
    instructions=(
        "Always confirm the order ID before issuing a refund. Check whether the "
        "order is delivered, returned, cancelled, disputed, or partially fulfilled. "
        "Never promise an instant refund when the payment rail has settlement delays. "
        "Explain the expected customer-visible timing and whether the refund returns "
        "to the original payment method, store credit, or a split tender. Escalate "
        "when the customer reports fraud, a chargeback, or a refund above the normal "
        "approval threshold."
    ),
    defer_loading=True,
)


@refunds.tool_plain
def refund_status(order_id: str) -> str:
    """Look up the refund status for an order."""
    return f"Order {order_id}: refund issued on 2026-05-01."


@refunds.tool_plain
def refund_eligibility(order_id: str, reason: str) -> str:
    """Check whether an order is eligible for refund based on order state and reason."""
    return (
        f"Order {order_id}: eligible for refund review for reason `{reason}`. "
        "Original payment method is available; expected settlement is 3-5 business days."
    )


@refunds.tool_plain
def create_refund_case(order_id: str, amount: float, reason: str) -> str:
    """Create a refund case for a reviewed order."""
    return (
        f"Refund case RF-{order_id[-4:]} opened for order {order_id} "
        f"for ${amount:.2f}; reason: {reason}."
    )

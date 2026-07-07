from __future__ import annotations

from pydantic_ai.capabilities import Capability

goodwill_credits = Capability(
    id="goodwill-credits",
    description=(
        "Use when a refund is not available or not the best remedy, but the customer may "
        "qualify for appeasement, courtesy credit, coupon, shipping credit, or loyalty points."
    ),
    instructions=(
        "Offer goodwill credits only after explaining the refund decision. Keep credits "
        "proportional to the inconvenience and avoid stacking multiple appeasements for "
        "the same incident. Prefer shipping credits for late deliveries, replacement "
        "coupons for damaged low-value goods, and loyalty points for service recovery. "
        "Do not present goodwill as an admission of liability. Escalate when the requested "
        "credit exceeds the configured support threshold or when the customer threatens "
        "legal action."
    ),
    defer_loading=True,
)


@goodwill_credits.tool_plain
def goodwill_options(order_id: str, issue: str) -> str:
    """Return eligible goodwill options for an order issue."""
    return (
        f"Order {order_id}: eligible goodwill for `{issue}` is a $10 shipping credit "
        "or 1,000 loyalty points."
    )


@goodwill_credits.tool_plain
def issue_goodwill_credit(order_id: str, credit_type: str, amount: float) -> str:
    """Issue an approved goodwill credit."""
    return (
        f"Goodwill {credit_type} credit for order {order_id} issued in the amount "
        f"of ${amount:.2f}."
    )

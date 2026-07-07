from __future__ import annotations

from pydantic_ai import Agent

from .capabilities.goodwill_credits import goodwill_options, issue_goodwill_credit
from .capabilities.order_lifecycle import cancellation_window, order_status
from .capabilities.payment_adjustments import calculate_adjustment, payment_tenders
from .capabilities.refund import (
    create_refund_case,
    refund_eligibility,
    refund_status,
)
from .capabilities.return_shipping import return_label, return_tracking
from .deps import AgentDeps


def register_refund_domain_tools(agent: Agent[AgentDeps, str]) -> Agent[AgentDeps, str]:
    for tool, capability in (
        (order_status, "order-lifecycle"),
        (cancellation_window, "order-lifecycle"),
        (refund_status, "refunds"),
        (refund_eligibility, "refunds"),
        (create_refund_case, "refunds"),
        (payment_tenders, "payment-adjustments"),
        (calculate_adjustment, "payment-adjustments"),
        (return_label, "return-shipping"),
        (return_tracking, "return-shipping"),
        (goodwill_options, "goodwill-credits"),
        (issue_goodwill_credit, "goodwill-credits"),
    ):
        agent.tool_plain(
            tool,
            metadata={"mode": "always-loaded-tools", "capability": capability},
            include_return_schema=True,
        )
    return agent

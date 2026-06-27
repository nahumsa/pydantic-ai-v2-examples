from __future__ import annotations

import sys
from typing import Literal

from loguru import logger
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability, HandleDeferredToolCalls
from pydantic_ai.tools import DeferredToolRequests, DeferredToolResults

from ..models import SupportDeskContext


EmailApprovalMode = Literal["ask", "approve", "skip"]


def build_customer_notification_capability() -> Capability[SupportDeskContext]:
    notification = Capability[SupportDeskContext](
        id="customer-notification",
        instructions=(
            "If service status is degraded or outage, call send_customer_email with the customer-facing "
            "message. This tool requires approval. Set email_action from the tool result, or use "
            "'email skipped' if approval is denied."
        ),
        description="Requests human approval before simulating a customer notification email.",
        defer_loading=True,
    )

    @notification.tool(metadata={"capability": "customer-notification"}, requires_approval=True)
    def send_customer_email(ctx: RunContext[SupportDeskContext], message: str) -> str:
        """Simulate sending an email to impacted customers after human approval."""
        logger.debug("simulated email sent customer={} message={!r}", ctx.deps.customer_name, message)
        return "email sent"

    return notification


def build_email_approval_handler(mode: EmailApprovalMode) -> HandleDeferredToolCalls[SupportDeskContext]:
    def handle_deferred(
        ctx: RunContext[SupportDeskContext], requests: DeferredToolRequests
    ) -> DeferredToolResults:
        if mode == "approve":
            logger.debug("email approval handler auto-approved")
            return requests.build_results(approve_all=True)

        approvals: dict[str, bool] = {}
        for call in requests.approvals:
            if mode == "skip":
                logger.debug("email approval handler auto-skipped tool={}", call.tool_name)
                approvals[call.tool_call_id] = False
                continue

            if not sys.stdin.isatty():
                logger.debug("email approval handler skipped non-interactive tool={}", call.tool_name)
                approvals[call.tool_call_id] = False
                continue

            print()
            print(f"Approve simulated email to impacted {ctx.deps.customer_name} customers?")
            print(f"Tool args: {call.args}")
            answer = input("Send email? [y/N]: ").strip().casefold()
            approvals[call.tool_call_id] = answer in {"y", "yes"}

        return requests.build_results(approvals=approvals)

    return HandleDeferredToolCalls(handle_deferred, id="email-approval-handler")

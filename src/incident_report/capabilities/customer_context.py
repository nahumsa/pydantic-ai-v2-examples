from __future__ import annotations

from loguru import logger
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability

from ..models import SupportDeskContext


def build_customer_context_capability() -> Capability[SupportDeskContext]:
    customer_context = Capability[SupportDeskContext](
        id="customer-context",
        description="Adds customer tier, region, and account-size instructions to each run.",
        defer_loading=True,
    )

    @customer_context.instructions
    def add_customer_context(ctx: RunContext[SupportDeskContext]) -> str:
        deps = ctx.deps
        logger.debug(
            "adding customer context customer={} tier={} region={}",
            deps.customer_name,
            deps.contract_tier,
            deps.region,
        )
        return (
            f"Customer: {deps.customer_name}. Contract tier: {deps.contract_tier}. "
            f"Primary region: {deps.region}. Keep the answer brief."
        )

    return customer_context

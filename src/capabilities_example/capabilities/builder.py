from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from pydantic_ai.capabilities import (
    AgentCapability,
    IncludeToolReturnSchemas,
    SetToolMetadata,
)

from ..deps import AgentDeps
from .goodwill_credits import goodwill_credits
from .order_lifecycle import order_lifecycle
from .payment_adjustments import payment_adjustments
from .refund import refunds
from .return_shipping import return_shipping


@dataclass
class CapabilityBuilder:
    capabilities: list[AgentCapability] = field(default_factory=list)

    def add(self, capability: AgentCapability[AgentDeps]) -> Self:
        self.capabilities.append(capability)
        return self

    def add_refunds(self) -> Self:
        return self.add(refunds)

    def add_order_lifecycle(self) -> Self:
        return self.add(order_lifecycle)

    def add_payment_adjustments(self) -> Self:
        return self.add(payment_adjustments)

    def add_return_shipping(self) -> Self:
        return self.add(return_shipping)

    def add_goodwill_credits(self) -> Self:
        return self.add(goodwill_credits)

    def include_tool_return_schemas(self) -> Self:
        return self.add(IncludeToolReturnSchemas())

    def add_tool_metadata(self, **metadata: object) -> Self:
        return self.add(SetToolMetadata(**metadata))

    def build(self) -> list[AgentCapability[AgentDeps]]:
        return list(self.capabilities)

    @classmethod
    def default(cls) -> Self:
        return (
            cls()
            .add_order_lifecycle()
            .add_refunds()
            .add_payment_adjustments()
            .add_return_shipping()
            .add_goodwill_credits()
            .include_tool_return_schemas()
            .add_tool_metadata(example="capabilities")
        )


def build_capabilities() -> list[AgentCapability[AgentDeps]]:
    return CapabilityBuilder.default().build()

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from pydantic_ai.capabilities import AgentCapability, IncludeToolReturnSchemas, SetToolMetadata

from ..models import SupportDeskContext
from .customer_context import build_customer_context_capability
from .customer_notification import EmailApprovalMode, build_customer_notification_capability, build_email_approval_handler
from .incident_intelligence import build_incident_intelligence_capability


@dataclass
class CapabilityBuilder:
    capabilities: list[AgentCapability[SupportDeskContext]] = field(default_factory=list)

    def add(self, capability: AgentCapability[SupportDeskContext]) -> Self:
        self.capabilities.append(capability)
        return self

    def add_customer_context(self) -> Self:
        return self.add(build_customer_context_capability())

    def add_incident_intelligence(self) -> Self:
        return self.add(build_incident_intelligence_capability())

    def add_customer_notification(self) -> Self:
        return self.add(build_customer_notification_capability())

    def handle_email_approval(self, mode: EmailApprovalMode = "ask") -> Self:
        return self.add(build_email_approval_handler(mode))

    def include_tool_return_schemas(self) -> Self:
        return self.add(IncludeToolReturnSchemas())

    def add_tool_metadata(self, **metadata: object) -> Self:
        return self.add(SetToolMetadata(**metadata))

    def build(self) -> list[AgentCapability[SupportDeskContext]]:
        return list(self.capabilities)

    @classmethod
    def default(cls, *, email_approval_mode: EmailApprovalMode = "ask") -> Self:
        return (
            cls()
            .add_customer_context()
            .add_incident_intelligence()
            .add_customer_notification()
            .handle_email_approval(email_approval_mode)
            .include_tool_return_schemas()
            .add_tool_metadata(example="service-status-triage")
        )


def build_capabilities(
    *, email_approval_mode: EmailApprovalMode = "ask"
) -> list[AgentCapability[SupportDeskContext]]:
    return CapabilityBuilder.default(email_approval_mode=email_approval_mode).build()

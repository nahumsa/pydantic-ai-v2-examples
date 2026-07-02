from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from pydantic_ai.capabilities import AgentCapability, IncludeToolReturnSchemas, SetToolMetadata

from ..deps import AnalystAgentDeps
from .abc_analysis import build_abc_analysis_capability


@dataclass
class CapabilityBuilder:
    capabilities: list[AgentCapability[AnalystAgentDeps]] = field(default_factory=list)

    def add(self, capability: AgentCapability[AnalystAgentDeps]) -> Self:
        self.capabilities.append(capability)
        return self

    def add_abc_analysis(self) -> Self:
        return self.add(build_abc_analysis_capability())

    def include_tool_return_schemas(self) -> Self:
        return self.add(IncludeToolReturnSchemas())

    def add_tool_metadata(self, **metadata: object) -> Self:
        return self.add(SetToolMetadata(**metadata))

    def build(self) -> list[AgentCapability[AnalystAgentDeps]]:
        return list(self.capabilities)

    @classmethod
    def default(cls) -> Self:
        return (
            cls()
            .add_abc_analysis()
            .include_tool_return_schemas()
            .add_tool_metadata(example="data-analyst")
        )


def build_capabilities() -> list[AgentCapability[AnalystAgentDeps]]:
    return CapabilityBuilder.default().build()

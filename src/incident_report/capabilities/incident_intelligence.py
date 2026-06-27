from __future__ import annotations

from loguru import logger
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability

from ..models import StatusEvent, SupportDeskContext


def build_incident_intelligence_capability() -> Capability[SupportDeskContext]:
    incident_intelligence = Capability[SupportDeskContext](
        id="incident-intelligence",
        instructions="Use lookup_service_status once before summarizing service health.",
        description="Looks up recent service health events.",
        defer_loading=True,
    )

    @incident_intelligence.tool(metadata={"capability": "incident-intelligence"})
    def lookup_service_status(
        ctx: RunContext[SupportDeskContext], service: str
    ) -> list[StatusEvent]:
        """Return known status events for a service name such as api, auth, billing, or search."""
        service_l = service.casefold()
        matches = [
            event
            for event in ctx.deps.status_events
            if service_l in event.service.casefold()
        ]
        logger.debug(
            "lookup_service_status service={} matches={}", service, len(matches)
        )
        return matches

    return incident_intelligence

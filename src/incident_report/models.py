from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


class StatusEvent(BaseModel):
    service: str
    state: Literal["operational", "degraded", "outage"]
    region: str
    minutes_ago: int
    note: str


class ServiceTriageReport(BaseModel):
    """Structured answer returned by the agent."""

    service: str
    status: Literal["operational", "degraded", "outage"]
    summary: str = Field(max_length=240)
    next_action: str = Field(max_length=160)
    customer_message: str = Field(max_length=240)
    email_action: Literal["email sent", "email skipped", "email not needed"]
    confidence: float = Field(ge=0, le=1)


@dataclass(frozen=True)
class SupportDeskContext:
    customer_name: str
    contract_tier: Literal["free", "pro", "enterprise"]
    region: str
    status_events: tuple[StatusEvent, ...]


@dataclass(frozen=True)
class SyntheticCase:
    """A reusable prompt/context pair for evaluating agent behavior."""

    case_id: str
    description: str
    prompt: str
    context: SupportDeskContext
    expected_service: str
    expected_status: Literal["operational", "degraded", "outage"]
    expected_email_action: Literal["email sent", "email skipped", "email not needed"]

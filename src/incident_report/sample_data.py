from __future__ import annotations

from loguru import logger

from .models import SupportDeskContext
from .synthetic_cases import get_synthetic_case


def sample_context() -> SupportDeskContext:
    context = get_synthetic_case("search-outage").context
    logger.debug(
        "created sample context customer={} status_events={}",
        context.customer_name,
        len(context.status_events),
    )
    return context

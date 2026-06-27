from __future__ import annotations

from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings

from .capabilities import EmailApprovalMode, build_capabilities
from .models import ServiceTriageReport, SupportDeskContext


def build_agent(
    *,
    model: OpenRouterModel,
    temperature: float = 0.2,
    max_tokens: int = 350,
    email_approval_mode: EmailApprovalMode = "ask",
) -> Agent[SupportDeskContext, ServiceTriageReport]:
    logger.debug(
        "building agent model={} temperature={} max_tokens={}",
        getattr(model, "model_name", type(model).__name__),
        temperature,
        max_tokens,
    )
    agent = Agent(
        model,
        output_type=ServiceTriageReport,
        deps_type=SupportDeskContext,
        instructions=(
            "You summarize one service health issue. Use concise fields only. "
            "For degraded or outage status, request approval through the customer notification tool. "
            "Do not include extra explanation outside the structured output."
        ),
        model_settings=OpenRouterModelSettings(
            temperature=temperature,
            max_tokens=max_tokens,
            parallel_tool_calls=True,
            openrouter_provider={"sort": "price", "allow_fallbacks": True},
            openrouter_usage={"include": True},
            openrouter_cache_tool_definitions="5m",
        ),
        retries=4,
        tool_timeout=8,
        capabilities=build_capabilities(email_approval_mode=email_approval_mode),
    )
    return agent

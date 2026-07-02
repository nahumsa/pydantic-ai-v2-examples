from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings

from .capabilities import build_capabilities
from .constants import DEFAULT_MODEL_MAX_TOKENS, INSTRUCTIONS
from .deps import AnalystAgentDeps
from .tools import register_tools


def build_analyst_agent(
    *,
    model: OpenRouterModel,
    temperature: float = 0.2,
    max_tokens: int = DEFAULT_MODEL_MAX_TOKENS,
) -> Agent[AnalystAgentDeps, str]:
    agent = Agent(
        model,
        deps_type=AnalystAgentDeps,
        instructions=INSTRUCTIONS,
        model_settings=OpenRouterModelSettings(
            temperature=temperature,
            max_tokens=max_tokens,
            parallel_tool_calls=True,
            openrouter_provider={"sort": "price", "allow_fallbacks": True},
            openrouter_usage={"include": True},
            openrouter_cache_tool_definitions="5m",
        ),
        retries=4,
        tool_timeout=60,
        capabilities=build_capabilities(),
    )
    return register_tools(agent)

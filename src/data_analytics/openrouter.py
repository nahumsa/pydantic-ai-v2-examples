from __future__ import annotations

from loguru import logger
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider


def build_openrouter_model(
    *,
    api_key: str | None,
    model_name: str,
    app_title: str,
    app_url: str | None = None,
) -> OpenRouterModel:
    logger.debug(
        "building OpenRouter model model_name={} app_title={} app_url={} api_key_set={}",
        model_name,
        app_title,
        app_url,
        bool(api_key),
    )
    provider = OpenRouterProvider(api_key=api_key, app_title=app_title, app_url=app_url)
    return OpenRouterModel(model_name, provider=provider)

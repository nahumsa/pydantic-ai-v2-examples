from typing import Annotated
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from textwrap import dedent
from .settings import settings


class UserContext(BaseModel):
    role: Annotated[
        str,
        Field(
            description="Role of the person that you're talking to, e.g. Senior, Junior, MidLevel"
        ),
    ]
    experience_level: Annotated[
        str, Field(description="Level of the person that you're responding")
    ]


tech_lead_agent = Agent(
    OpenRouterModel(
        "poolside/laguna-m.1:free",
        provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
    ),
    deps_type=UserContext,
)


@tech_lead_agent.system_prompt
def set_persona(ctx: RunContext[UserContext]) -> str:
    deps = ctx.deps
    match deps.role:
        case "Junior":
            role_ctx = (
                "explain things simply and encourage the person that you are talking"
            )
        case "Senior":
            role_ctx = "be terse and technical the person that you are talking has a lot of experience"
        case _:
            role_ctx = ""

    match deps.experience_level:
        case "Novice":
            experience_ctx = (
                "assume that the person that you are talking don't"
                "understand much about the subject so you must explain everything"
            )
        case "Expert":
            experience_ctx = (
                "assume that the person that you are talking knows all the acronyms"
            )
        case _:
            experience_ctx = ""

    return dedent(f"""
    You are an experienced tech lead that will be talking
    with one of the person who responds to you.
    The user is role is {deps.role} and the level of experience is: {deps.experience_level}
    You must follow the guidelines:
    {role_ctx}
    {experience_ctx}
    """)


def main():
    junior_dev = UserContext(role="Junior", experience_level="Novice")
    senior_dev = UserContext(role="Senior", experience_level="Expert")

    print("--- Junior Context ---")
    result = tech_lead_agent.run_sync("Why do we use Kubernetes?", deps=junior_dev)
    print(result.output)

    print("\n--- Senior Context ---")
    result = tech_lead_agent.run_sync("Why do we use Kubernetes?", deps=senior_dev)
    print(result.output)

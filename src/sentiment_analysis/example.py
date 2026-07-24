from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from .settings import settings


class SentimentAnalysis(BaseModel):
    """Model for sentiment analysis results"""

    sentiment: str = Field(
        description="The sentiment: 'positive', 'negative', or 'neutral'"
    )
    score: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    reasoning: str = Field(
        description="Brief explanation of why this sentiment was chosen"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Key words or phrases that influenced the analysis",
    )

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str) -> str:
        """Ensure sentiment is one of the valid values"""
        valid = {"positive", "negative", "neutral"}
        if v.lower() not in valid:
            raise ValueError(f"Sentiment must be one of {valid}")
        return v.lower()


def print_sentiment_analysis(result):
    print("Sentiment Analysis Result:")
    print(f"Sentiment: {result.sentiment}")
    print(f"Score: {result.score:.2f}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Keywords: {result.keywords}")


def analyze_sentiment(text: str) -> SentimentAnalysis:
    """Use OpenAI API with Pydantic model for structured output"""

    client = Agent(
        OpenRouterModel(
            "poolside/laguna-m.1:free",
            provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
        ),
        system_prompt="You are a sentiment analysis expert. Analyze the sentiment of the given text.",
        output_type=SentimentAnalysis,
    )

    response = client.run_sync(f"Analyze the sentiment of this text: {text}")

    parsed = response.output
    if parsed is None:
        raise ValueError("Failed to parse response as SentimentAnalysis")
    return parsed


def main():
    result = analyze_sentiment(
        "I absolutely love this new Python library! It's amazing!"
    )
    print_sentiment_analysis(result)

    result = analyze_sentiment(
        r"I **absolutely** love this new Python library! It's so amazing! /s"
    )
    print_sentiment_analysis(result)

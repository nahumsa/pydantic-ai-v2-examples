from __future__ import annotations

import argparse
import os
import sys

from loguru import logger
from pydantic_ai.usage import UsageLimits
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agent import build_agent
from .capabilities import EmailApprovalMode
from .openrouter import build_openrouter_model
from .report_writer import write_markdown_report
from .sample_data import sample_context
from .synthetic_cases import (
    get_random_synthetic_case,
    get_synthetic_case,
    list_synthetic_cases,
    synthetic_case_ids,
)

DEFAULT_PROMPT = (
    "Northstar Clinic says search is timing out. Check the search status and summarize what to do next."
)
DEFAULT_REQUEST_LIMIT = 8
DEFAULT_OUTPUT_TOKEN_LIMIT = 1_200
DEFAULT_MODEL_MAX_TOKENS = 350


def env_flag(name: str) -> bool:
    return os.getenv(name, "").casefold() in {"1", "true", "yes", "on"}


def configure_logging(debug: bool) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if debug else "WARNING",
        colorize=sys.stderr.isatty(),
        backtrace=debug,
        diagnose=debug,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan> | {message}",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pydantic AI v2 OpenRouter service-status triage example"
    )
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT)
    case_group = parser.add_mutually_exclusive_group()
    case_group.add_argument(
        "--case",
        choices=synthetic_case_ids(),
        help="Run one synthetic test case, using its prompt and support context.",
    )
    case_group.add_argument(
        "--random-case",
        action="store_true",
        help="Run a random synthetic test case from the SQLite database.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List available synthetic test cases and exit.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free"),
        help="OpenRouter model slug, for example openai/gpt-4o-mini or anthropic/claude-3.5-haiku",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--request-limit",
        type=int,
        default=DEFAULT_REQUEST_LIMIT,
        help=f"Maximum Pydantic AI model requests per run. Defaults to {DEFAULT_REQUEST_LIMIT}.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MODEL_MAX_TOKENS,
        help=f"Maximum model output tokens per request. Defaults to {DEFAULT_MODEL_MAX_TOKENS}.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=env_flag("DEBUG") or env_flag("PYDANTIC_AI_EXAMPLE_DEBUG"),
        help="Enable debug logs. Can also be set with DEBUG=1 or PYDANTIC_AI_EXAMPLE_DEBUG=1.",
    )
    email_group = parser.add_mutually_exclusive_group()
    email_group.add_argument(
        "--approve-email",
        action="store_true",
        help='Approve the simulated customer email and return "email sent".',
    )
    email_group.add_argument(
        "--skip-email",
        action="store_true",
        help='Skip the simulated customer email and return "email skipped".',
    )
    return parser


def email_approval_mode(*, approve: bool, skip: bool) -> EmailApprovalMode:
    if approve:
        return "approve"
    if skip:
        return "skip"
    return "ask"


def main() -> None:
    args = build_parser().parse_args()
    configure_logging(args.debug)
    console = Console()
    approval_mode = email_approval_mode(approve=args.approve_email, skip=args.skip_email)

    if args.list_cases:
        table = Table(title="Synthetic Test Cases")
        table.add_column("Case")
        table.add_column("Expected")
        table.add_column("Email")
        table.add_column("Description")
        for case in list_synthetic_cases():
            table.add_row(
                case.case_id,
                f"{case.expected_service}/{case.expected_status}",
                case.expected_email_action,
                case.description,
            )
        console.print(table)
        return

    if args.random_case:
        synthetic_case = get_random_synthetic_case()
        console.print(f"Random case: {synthetic_case.case_id}")
    else:
        synthetic_case = get_synthetic_case(args.case) if args.case else None
    prompt = synthetic_case.prompt if synthetic_case else args.prompt
    context = synthetic_case.context if synthetic_case else sample_context()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY.")
    logger.debug("using OpenRouter model={} app_url={}", args.model, os.getenv("OPENROUTER_APP_URL"))
    model = build_openrouter_model(
        api_key=api_key,
        model_name=args.model,
        app_title="pydantic-ai-v2-openrouter-example",
        app_url=os.getenv("OPENROUTER_APP_URL"),
    )

    if synthetic_case:
        logger.debug(
            "running synthetic case case_id={} expected_service={} expected_status={}",
            synthetic_case.case_id,
            synthetic_case.expected_service,
            synthetic_case.expected_status,
        )
    logger.debug("running agent prompt={!r}", prompt)
    agent = build_agent(
        model=model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        email_approval_mode=approval_mode,
    )
    result = agent.run_sync(
        prompt,
        deps=context,
        usage_limits=UsageLimits(
            request_limit=args.request_limit,
            tool_calls_limit=2,
            output_tokens_limit=DEFAULT_OUTPUT_TOKEN_LIMIT,
        ),
    )
    logger.debug("agent run complete usage={}", result.usage)

    report = result.output
    report_path = write_markdown_report(report, context)
    console.print(
        Panel.fit(report.model_dump_json(indent=2), title="Service Triage Report")
    )
    console.print(f"Email action: {report.email_action}")
    if synthetic_case:
        console.print(
            "Expected: "
            f"service={synthetic_case.expected_service}, "
            f"status={synthetic_case.expected_status}, "
            f"email_action={synthetic_case.expected_email_action}"
        )
    console.print(f"Markdown report: {report_path}")
    console.print(f"Usage: {result.usage}")

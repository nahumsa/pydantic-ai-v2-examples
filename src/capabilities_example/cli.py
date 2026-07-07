from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.usage import UsageLimits
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .agent import build_analyst_agent
from .benchmark import (
    BenchmarkConfig,
    print_benchmark_details,
    print_benchmark_summary,
    run_benchmark,
    write_benchmark_csv,
)
from .constants import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_MAX_TOKENS,
    DEFAULT_OUTPUT_TOKEN_LIMIT,
    DEFAULT_REQUEST_LIMIT,
)
from .deps import AgentDeps
from .openrouter import build_openrouter_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pydantic AI v2 OpenRouter data analyst example"
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
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
        "--chat",
        action="store_true",
        help="Start an interactive chat session. Use :tables, :history, :context, :help, or :quit inside the session.",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run the built-in refund-domain prompt benchmark instead of chat.",
    )
    parser.add_argument(
        "--benchmark-rounds",
        type=int,
        default=3,
        help="Number of rounds to run for each benchmark prompt and mode. Defaults to 3.",
    )
    parser.add_argument(
        "--benchmark-modes",
        nargs="+",
        choices=("capabilities", "always"),
        default=("capabilities", "always"),
        help="Tool modes to benchmark. Defaults to capabilities always.",
    )
    parser.add_argument(
        "--benchmark-output",
        default="reports/capabilities_benchmark.csv",
        help=(
            "CSV path for benchmark results. Defaults to "
            "reports/capabilities_benchmark.csv."
        ),
    )
    parser.add_argument(
        "--rate-limit-retries",
        type=int,
        default=4,
        help="Number of retries for OpenRouter 429 responses during benchmarks. Defaults to 4.",
    )
    parser.add_argument(
        "--rate-limit-backoff",
        type=float,
        default=2.0,
        help="Initial backoff in seconds for OpenRouter 429 responses. Defaults to 2.0.",
    )
    parser.add_argument(
        "--rate-limit-max-backoff",
        type=float,
        default=30.0,
        help="Maximum backoff in seconds for OpenRouter 429 responses. Defaults to 30.0.",
    )
    parser.add_argument(
        "--tool-mode",
        choices=("capabilities", "always", "none"),
        default="capabilities",
        help=(
            "Tool registration mode: deferred capabilities, all refund-domain tools "
            "always loaded, or no tools. Defaults to capabilities."
        ),
    )
    parser.add_argument(
        "--no-capabilities",
        action="store_true",
        help="Compatibility alias for --tool-mode none.",
    )
    return parser


def usage_limits(args: argparse.Namespace) -> UsageLimits:
    return UsageLimits(
        request_limit=args.request_limit,
        output_tokens_limit=DEFAULT_OUTPUT_TOKEN_LIMIT,
    )


def print_tables(console: Console, deps: AgentDeps) -> None:
    if not deps.output:
        console.print("[yellow]No datasets loaded.[/yellow]")
        return

    for ref, dataframe in deps.output.items():
        columns = ", ".join(str(column) for column in dataframe.columns)
        console.print(
            f"[green]{ref}[/green]: [cyan]{len(dataframe)} rows[/cyan]; "
            f"[dim]columns:[/dim] {columns}"
        )


def format_bytes(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        value /= 1024
    return f"{size} B"


def message_history_size(message_history: list[Any]) -> int:
    if not message_history:
        return 0
    return len(ModelMessagesTypeAdapter.dump_json(message_history))


def dataframe_memory_size(deps: AgentDeps) -> int:
    return sum(
        int(dataframe.memory_usage(index=True, deep=True).sum())
        for dataframe in deps.output.values()
    )


def print_context_size(
    console: Console,
    message_history: list[Any],
    tool_history: list[str],
    deps: AgentDeps,
) -> None:
    history_bytes = message_history_size(message_history)
    tool_history_bytes = len("\n".join(tool_history).encode())
    dataframe_bytes = dataframe_memory_size(deps)
    dataframe_rows = sum(len(dataframe) for dataframe in deps.output.values())

    table = Table(title="Context Size")
    table.add_column("Scope", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Serialized Size", justify="right", style="green")
    table.add_row(
        "message history",
        f"{len(message_history)} messages",
        format_bytes(history_bytes),
    )
    table.add_row(
        "tool history summary",
        f"{len(tool_history)} events",
        format_bytes(tool_history_bytes),
    )
    table.add_row(
        "loaded DataFrames",
        f"{len(deps.output)} tables / {dataframe_rows} rows",
        format_bytes(dataframe_bytes),
    )
    table.add_row(
        "total local footprint",
        "",
        format_bytes(history_bytes + tool_history_bytes + dataframe_bytes),
    )
    console.print(table)
    console.print(
        "[dim]Note: DataFrames are runtime deps; only tool outputs and displayed rows enter model message history.[/dim]"
    )


def summarize_value(value: object, *, max_length: int = 220) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, default=str, ensure_ascii=False)
        except TypeError:
            text = repr(value)

    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def summarize_tool_events(messages: list[Any]) -> list[str]:
    events: list[str] = []
    for message in messages:
        for part in getattr(message, "parts", ()):
            part_kind = getattr(part, "part_kind", None)
            tool_kind = getattr(part, "tool_kind", None)
            tool_name = getattr(part, "tool_name", None)
            if part_kind == "tool-call" and tool_name:
                args = getattr(part, "args", None)
                events.append(f"call {tool_name} args={summarize_value(args)}")
            elif part_kind == "tool-return" and tool_name:
                content = getattr(part, "content", None)
                outcome = getattr(part, "outcome", "success")
                events.append(
                    f"return {tool_name} outcome={outcome} content={summarize_value(content)}"
                )
            elif tool_kind == "capability-load" and tool_name:
                args = getattr(part, "args", None)
                content = getattr(part, "content", None)
                if args is not None:
                    events.append(f"call {tool_name} args={summarize_value(args)}")
                elif content is not None:
                    events.append(
                        f"return {tool_name} content={summarize_value(content)}"
                    )
    return events


def print_tool_events(console: Console, events: list[str]) -> None:
    if not events:
        console.print("[dim]Tools: none[/dim]")
        return

    console.print("[bold cyan]Tools[/bold cyan]")
    for event in events:
        if event.startswith("call "):
            console.print(Text(f"- {event}", style="cyan"))
        elif event.startswith("return "):
            console.print(Text(f"- {event}", style="green"))
        else:
            console.print(Text(f"- {event}", style="dim"))


def print_agent_response(console: Console, output: str) -> None:
    console.print(Panel(output, title="Agent", border_style="magenta"))


def print_model_usage(console: Console, usage: Any) -> None:
    table = Table(title="Model Usage")
    table.add_column("Metric", style="cyan")
    table.add_column("Tokens", justify="right", style="green")
    table.add_row("input", str(getattr(usage, "input_tokens", 0)))
    table.add_row("output", str(getattr(usage, "output_tokens", 0)))
    table.add_row("cache write", str(getattr(usage, "cache_write_tokens", 0)))
    table.add_row("cache read", str(getattr(usage, "cache_read_tokens", 0)))
    table.add_row("total", str(getattr(usage, "total_tokens", 0)))
    console.print(table)


def run_chat(
    agent: Agent[AgentDeps, str],
    deps: AgentDeps,
    args: argparse.Namespace,
    console: Console,
) -> None:
    if not sys.stdin.isatty():
        raise SystemExit("--chat requires an interactive terminal.")

    console.print(
        "[bold magenta]Data analyst chat.[/bold magenta] "
        "[dim]Type :help for commands or :quit to exit.[/dim]"
    )
    console.print(
        "[dim]Capabilities: "
        f"{'enabled' if args.tool_mode == 'capabilities' else 'disabled'}; "
        f"tool mode: {args.tool_mode}.[/dim]"
    )
    message_history: list[Any] = []
    tool_history: list[str] = []
    prompt = None

    while True:
        if prompt is None:
            prompt = input("you> ").strip()
        else:
            prompt = prompt.strip()

        if not prompt:
            prompt = None
            continue
        if prompt in {":quit", ":q", "quit", "exit"}:
            return
        if prompt == ":help":
            console.print(
                "[bold]Commands[/bold]: "
                "[cyan]:tables[/cyan] shows loaded DataFrames, "
                "[cyan]:history[/cyan] shows tool calls, "
                "[cyan]:context[/cyan] shows context size, "
                "[cyan]:quit[/cyan] exits."
            )
            prompt = None
            continue
        if prompt in {":context", ":context-size"}:
            print_context_size(console, message_history, tool_history, deps)
            prompt = None
            continue

        previous_message_count = len(message_history)
        result = agent.run_sync(
            user_prompt=prompt,
            deps=deps,
            message_history=message_history,
            usage_limits=usage_limits(args),
        )
        all_messages = result.all_messages()
        new_tool_events = summarize_tool_events(all_messages[previous_message_count:])
        tool_history.extend(new_tool_events)
        message_history = all_messages
        print_tool_events(console, new_tool_events)
        print_model_usage(console, result.usage)
        print_agent_response(console, result.output)
        prompt = None


def main() -> None:
    args = build_parser().parse_args()
    if args.no_capabilities:
        args.tool_mode = "none"
    console = Console()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY.")

    model = build_openrouter_model(
        api_key=api_key,
        model_name=args.model,
        app_title="pydantic-ai-v2-openrouter-capabilities",
        app_url=os.getenv("OPENROUTER_APP_URL"),
    )
    if args.benchmark:
        try:
            results = run_benchmark(
                model=model,
                config=BenchmarkConfig(
                    rounds=args.benchmark_rounds,
                    modes=tuple(args.benchmark_modes),
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    usage_limits=usage_limits(args),
                    rate_limit_retries=args.rate_limit_retries,
                    rate_limit_backoff_seconds=args.rate_limit_backoff,
                    rate_limit_max_backoff_seconds=args.rate_limit_max_backoff,
                ),
                console=console,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print_benchmark_summary(console, results)
        print_benchmark_details(console, results)
        output_path = write_benchmark_csv(args.benchmark_output, results)
        console.print(f"[green]Benchmark CSV saved to {output_path}[/green]")
        return

    agent = build_analyst_agent(
        model=model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        tool_mode=args.tool_mode,
    )
    deps = AgentDeps(customer_name="fulano")
    run_chat(agent, deps, args, console)

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
from .constants import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_MAX_TOKENS,
    DEFAULT_OUTPUT_TOKEN_LIMIT,
    DEFAULT_PROMPT,
    DEFAULT_REQUEST_LIMIT,
)
from .deps import AnalystAgentDeps
from .openrouter import build_openrouter_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pydantic AI v2 OpenRouter data analyst example"
    )
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT)
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
    return parser


def usage_limits(args: argparse.Namespace) -> UsageLimits:
    return UsageLimits(
        request_limit=args.request_limit,
        output_tokens_limit=DEFAULT_OUTPUT_TOKEN_LIMIT,
    )


def print_tables(console: Console, deps: AnalystAgentDeps) -> None:
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


def dataframe_memory_size(deps: AnalystAgentDeps) -> int:
    return sum(
        int(dataframe.memory_usage(index=True, deep=True).sum())
        for dataframe in deps.output.values()
    )


def print_context_size(
    console: Console,
    message_history: list[Any],
    tool_history: list[str],
    deps: AnalystAgentDeps,
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


def run_once(
    agent: Agent[AnalystAgentDeps, str],
    deps: AnalystAgentDeps,
    args: argparse.Namespace,
    console: Console,
) -> None:
    result = agent.run_sync(
        user_prompt=args.prompt,
        deps=deps,
        usage_limits=usage_limits(args),
    )
    print_tool_events(console, summarize_tool_events(result.all_messages()))
    print_agent_response(console, result.output)


def run_chat(
    agent: Agent[AnalystAgentDeps, str],
    deps: AnalystAgentDeps,
    args: argparse.Namespace,
    console: Console,
) -> None:
    if not sys.stdin.isatty():
        raise SystemExit("--chat requires an interactive terminal.")

    console.print(
        "[bold magenta]Data analyst chat.[/bold magenta] "
        "[dim]Type :help for commands or :quit to exit.[/dim]"
    )
    message_history: list[Any] = []
    tool_history: list[str] = []
    prompt = args.prompt if args.prompt != DEFAULT_PROMPT else None

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
        if prompt == ":tables":
            print_tables(console, deps)
            prompt = None
            continue
        if prompt == ":history":
            print_tool_events(console, tool_history)
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
        print_agent_response(console, result.output)
        prompt = None


def main() -> None:
    args = build_parser().parse_args()
    console = Console()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY.")

    model = build_openrouter_model(
        api_key=api_key,
        model_name=args.model,
        app_title="pydantic-ai-v2-openrouter-data-analyst",
        app_url=os.getenv("OPENROUTER_APP_URL"),
    )
    agent = build_analyst_agent(
        model=model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    deps = AnalystAgentDeps()
    if args.chat:
        run_chat(agent, deps, args, console)
    else:
        run_once(agent, deps, args, console)

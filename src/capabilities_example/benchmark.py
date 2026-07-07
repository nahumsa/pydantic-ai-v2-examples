from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic_ai import Agent, ModelHTTPError
from pydantic_ai.usage import UsageLimits
from rich.console import Console
from rich.table import Table

from .agent import ToolMode, build_analyst_agent
from .deps import AgentDeps


@dataclass(frozen=True)
class BenchmarkConfig:
    rounds: int
    modes: tuple[ToolMode, ...]
    temperature: float
    max_tokens: int
    usage_limits: UsageLimits
    rate_limit_retries: int = 4
    rate_limit_backoff_seconds: float = 2.0
    rate_limit_max_backoff_seconds: float = 30.0


@dataclass(frozen=True)
class BenchmarkPrompt:
    name: str
    prompt: str
    expected_tools: tuple[str, ...]


@dataclass
class BenchmarkResult:
    round_number: int
    mode: ToolMode
    prompt_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    called_tools: tuple[str, ...]
    passed: bool
    error: str | None = None


BENCHMARK_PROMPTS = (
    BenchmarkPrompt(
        name="refund-status",
        prompt=(
            "Use the available tools to answer: what is the refund status for "
            "order ORD-1001?"
        ),
        expected_tools=("refund_status",),
    ),
    BenchmarkPrompt(
        name="cancel-or-refund",
        prompt=(
            "Use the available tools to check whether order ORD-2002 can still be "
            "cancelled, or whether I need a refund or return path instead."
        ),
        expected_tools=("cancellation_window",),
    ),
    BenchmarkPrompt(
        name="split-tender-adjustment",
        prompt=(
            "Use the available tools to calculate a price adjustment for order "
            "ORD-3003. I paid with a card and store credit."
        ),
        expected_tools=("calculate_adjustment",),
    ),
    BenchmarkPrompt(
        name="return-label",
        prompt=(
            "Use the available tools to get a return shipping label for order ORD-4004."
        ),
        expected_tools=("return_label",),
    ),
    BenchmarkPrompt(
        name="goodwill-options",
        prompt=(
            "Use the available tools to find goodwill options for order ORD-5005 "
            "because the delivery was late."
        ),
        expected_tools=("goodwill_options",),
    ),
)


def summarize_value(value: object, *, max_length: int = 220) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            import json

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
                    f"return {tool_name} outcome={outcome} "
                    f"content={summarize_value(content)}"
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


def called_tool_names(events: list[str]) -> tuple[str, ...]:
    names: list[str] = []
    for event in events:
        if not event.startswith("call "):
            continue
        name = event.removeprefix("call ").split(" ", 1)[0]
        names.append(name)
    return tuple(names)


def benchmark_passed(
    called_tools: tuple[str, ...],
    expected_tools: tuple[str, ...],
) -> bool:
    return any(tool in called_tools for tool in expected_tools)


def run_agent_with_rate_limit_backoff(
    agent: Agent[AgentDeps, str],
    *,
    prompt: BenchmarkPrompt,
    config: BenchmarkConfig,
    console: Console,
) -> Any:
    attempt = 0
    while True:
        try:
            return agent.run_sync(
                user_prompt=prompt.prompt,
                deps=AgentDeps(customer_name="fulano"),
                message_history=[],
                usage_limits=config.usage_limits,
            )
        except ModelHTTPError as exc:
            if exc.status_code != 429 or attempt >= config.rate_limit_retries:
                raise
            delay = min(
                config.rate_limit_backoff_seconds * (2**attempt),
                config.rate_limit_max_backoff_seconds,
            )
            attempt += 1
            console.print(
                "[yellow]OpenRouter rate limit hit; "
                f"retrying {prompt.name} in {delay:.1f}s "
                f"(attempt {attempt}/{config.rate_limit_retries}).[/yellow]"
            )
            time.sleep(delay)


def run_benchmark(
    *,
    model: Any,
    config: BenchmarkConfig,
    console: Console,
) -> list[BenchmarkResult]:
    if config.rounds < 1:
        raise ValueError("benchmark rounds must be at least 1")
    if config.rate_limit_retries < 0:
        raise ValueError("rate limit retries must be at least 0")
    if config.rate_limit_backoff_seconds < 0:
        raise ValueError("rate limit backoff must be at least 0")
    if config.rate_limit_max_backoff_seconds < 0:
        raise ValueError("rate limit max backoff must be at least 0")

    agents = {
        mode: build_analyst_agent(
            model=model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            tool_mode=mode,
        )
        for mode in config.modes
    }
    results: list[BenchmarkResult] = []

    console.print(
        "[bold magenta]Refund capability benchmark[/bold magenta] "
        f"[dim]{config.rounds} rounds; modes: {', '.join(config.modes)}.[/dim]"
    )
    console.print(
        "[dim]Each run uses fresh message history. Correctness means at least one "
        "expected domain tool call.[/dim]"
    )

    for round_number in range(1, config.rounds + 1):
        for prompt in BENCHMARK_PROMPTS:
            for mode, agent in agents.items():
                console.print(
                    f"[dim]round {round_number} | {mode} | {prompt.name}[/dim]"
                )
                try:
                    result = run_agent_with_rate_limit_backoff(
                        agent,
                        prompt=prompt,
                        config=config,
                        console=console,
                    )
                    messages = result.all_messages()
                    tools = called_tool_names(summarize_tool_events(messages))
                    usage = result.usage
                    results.append(
                        BenchmarkResult(
                            round_number=round_number,
                            mode=mode,
                            prompt_name=prompt.name,
                            input_tokens=getattr(usage, "input_tokens", 0),
                            output_tokens=getattr(usage, "output_tokens", 0),
                            total_tokens=getattr(usage, "total_tokens", 0),
                            cache_write_tokens=getattr(
                                usage, "cache_write_tokens", 0
                            ),
                            cache_read_tokens=getattr(usage, "cache_read_tokens", 0),
                            called_tools=tools,
                            passed=benchmark_passed(tools, prompt.expected_tools),
                        )
                    )
                except Exception as exc:
                    results.append(
                        BenchmarkResult(
                            round_number=round_number,
                            mode=mode,
                            prompt_name=prompt.name,
                            input_tokens=0,
                            output_tokens=0,
                            total_tokens=0,
                            cache_write_tokens=0,
                            cache_read_tokens=0,
                            called_tools=(),
                            passed=False,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )

    return results


def print_benchmark_summary(
    console: Console,
    results: list[BenchmarkResult],
) -> None:
    summary = Table(title="Benchmark Summary")
    summary.add_column("Mode", style="cyan")
    summary.add_column("Runs", justify="right")
    summary.add_column("Pass", justify="right", style="green")
    summary.add_column("Avg Input", justify="right")
    summary.add_column("Avg Output", justify="right")
    summary.add_column("Avg Total", justify="right")
    summary.add_column("Avg Cache Read", justify="right")

    for mode in ("capabilities", "always"):
        mode_results = [result for result in results if result.mode == mode]
        if not mode_results:
            continue
        successful_runs = [result for result in mode_results if result.error is None]
        pass_count = sum(result.passed for result in mode_results)
        if successful_runs:
            avg_input = round(mean(result.input_tokens for result in successful_runs))
            avg_output = round(mean(result.output_tokens for result in successful_runs))
            avg_total = round(mean(result.total_tokens for result in successful_runs))
            avg_cache_read = round(
                mean(result.cache_read_tokens for result in successful_runs)
            )
        else:
            avg_input = avg_output = avg_total = avg_cache_read = 0

        summary.add_row(
            mode,
            str(len(mode_results)),
            f"{pass_count}/{len(mode_results)}",
            str(avg_input),
            str(avg_output),
            str(avg_total),
            str(avg_cache_read),
        )
    console.print(summary)


def print_benchmark_details(
    console: Console,
    results: list[BenchmarkResult],
) -> None:
    details = Table(title="Benchmark Details")
    details.add_column("Round", justify="right")
    details.add_column("Mode", style="cyan")
    details.add_column("Prompt")
    details.add_column("Pass", justify="center")
    details.add_column("Input", justify="right")
    details.add_column("Total", justify="right")
    details.add_column("Called Tools", overflow="fold")
    details.add_column("Error", overflow="fold")

    for result in results:
        details.add_row(
            str(result.round_number),
            result.mode,
            result.prompt_name,
            "yes" if result.passed else "no",
            str(result.input_tokens),
            str(result.total_tokens),
            ", ".join(result.called_tools) if result.called_tools else "-",
            result.error or "-",
        )
    console.print(details)


def write_benchmark_csv(
    path: str | Path,
    results: list[BenchmarkResult],
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=(
                "round_number",
                "mode",
                "prompt_name",
                "passed",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cache_write_tokens",
                "cache_read_tokens",
                "called_tools",
                "error",
            ),
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "round_number": result.round_number,
                    "mode": result.mode,
                    "prompt_name": result.prompt_name,
                    "passed": result.passed,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "total_tokens": result.total_tokens,
                    "cache_write_tokens": result.cache_write_tokens,
                    "cache_read_tokens": result.cache_read_tokens,
                    "called_tools": "|".join(result.called_tools),
                    "error": result.error or "",
                }
            )
    return output_path

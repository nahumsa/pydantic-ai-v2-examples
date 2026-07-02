# Pydantic AI v2 + OpenRouter Examples

Small runnable examples of Pydantic AI v2 agents using OpenRouter. The repo is
focused on practical agent patterns: typed runtime deps, tools, capabilities,
chat history, and local data analysis.

## Quick Start

```bash
uv sync
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Run a case:

```bash
uv run incident-report
uv run data-analytics --chat
```

Use a different model with `--model` or `OPENROUTER_MODEL`.

## Cases

### Incident Report

A support-desk triage agent for SaaS service incidents. It checks customer and
service-status context, classifies the situation, optionally requests approval
for a customer email, and writes a Markdown triage report.

Useful commands:

```bash
uv run incident-report
uv run incident-report --list-cases
uv run incident-report --case auth-operational --skip-email
uv run incident-report --random-case --skip-email
```

### Data Analytics

A chat-oriented analyst agent for local supply-chain datasets. It can list and
load bundled CSVs, query loaded DataFrames with DuckDB, show tool-call history,
report context size, and run ABC/Pareto classification through a capability.

Useful commands:

```bash
uv run data-analytics --chat
uv run data-analytics "Load orders and run ABC analysis by product."
```

Chat commands:

```text
:tables
:history
:context
:help
:quit
```

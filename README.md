# Pydantic AI v2 + OpenRouter Example

This is a small, runnable example of a Pydantic AI v2 agent using OpenRouter.

The agent acts like a support-desk helper for a SaaS incident. Give it a short
customer report, and it checks recent service status data, decides whether the
service is operational, degraded, or down, and writes a structured triage report.
If the incident needs a customer notification, it asks for approval before
simulating an email.

The goal is to show a realistic Pydantic AI setup without turning the example
into a full application.

## What This Shows

- Running a Pydantic AI agent through OpenRouter.
- Passing typed runtime context with `deps_type`.
- Splitting agent behavior into reusable capabilities.
- Adding dynamic instructions from customer context.
- Registering tools on capabilities.
- Handling tools that require approval.
- Returning structured Pydantic output.
- Writing the final result to a Markdown report.

## Quick Start

Install the project:

```bash
uv sync
```

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Run the CLI:

```bash
uv run incident-report
```

That prints a JSON triage report and writes a Markdown file under `incident_report/`,
for example:

```text
incident_report/YYYYMMDD-HHMMSS-search-outage.md
```

## Run Against OpenRouter

By default, the example uses the model configured in the CLI. You can choose a
different OpenRouter model with either an environment variable:

```bash
OPENROUTER_MODEL="anthropic/claude-3.5-haiku" uv run incident-report
```

or the `--model` flag:

```bash
uv run incident-report --model "openai/gpt-4o-mini"
```

You can also pass your own incident prompt:

```bash
uv run incident-report \
  "Acme Bank says search is timing out. Check status and summarize the next action."
```

## Synthetic Test Cases

The repo includes a small SQLite database of synthetic incidents and
non-incidents at:

```text
src/incident_report/data/synthetic_cases.sqlite
```

List the available cases without calling OpenRouter:

```bash
uv run incident-report --list-cases
```

Run a specific case with its stored prompt, customer context, service status
events, and expected outcome:

```bash
uv run incident-report --case auth-operational --skip-email
```

Run a random synthetic case from the same SQLite database:

```bash
uv run incident-report --random-case --skip-email
```

Rebuild the SQLite database from the reviewable seed SQL:

```bash
uv run python scripts/build_synthetic_db.py
```

The seed SQL lives at:

```text
src/incident_report/data/synthetic_cases_seed.sql
```

## Useful Local Options

Enable debug logging:

```bash
uv run incident-report --debug
```

The same logging can be enabled with:

```bash
DEBUG=1 uv run incident-report
```

or:

```bash
PYDANTIC_AI_EXAMPLE_DEBUG=1 uv run incident-report
```

The CLI keeps Pydantic AI's hard `output_tokens_limit` at `1200`, while the
model setting `--max-tokens` defaults to `350`. That leaves room for multi-step
tool runs without blowing through the usage limit.

## How It Is Put Together

The main path is:

1. `cli.py` parses arguments, creates the OpenRouter model, and creates sample
   support-desk context.
2. `agent.py` builds the Pydantic AI agent with typed deps, structured output,
   model settings, usage limits, and capabilities.
3. The capabilities add customer context, look up service status, and handle the
   approval-gated customer email.
4. `report_writer.py` saves the final `ServiceTriageReport` as Markdown.

The default capability set is built here:

```python
CapabilityBuilder.default().build()
```

For a smaller agent, compose only the pieces you need:

```python
from incident_report.capabilities import CapabilityBuilder

capabilities = (
    CapabilityBuilder()
    .add_customer_context()
    .add_incident_intelligence()
    .include_tool_return_schemas()
    .add_tool_metadata(environment="production")
    .build()
)
```

## File Map

- `src/incident_report/cli.py` is the runnable command-line
  entry point.
- `src/incident_report/agent.py` assembles the agent.
- `src/incident_report/openrouter.py` creates the OpenRouter
  model and provider.
- `src/incident_report/models.py` defines the runtime context and
  structured output models.
- `src/incident_report/capabilities/` contains one capability per
  behavior: customer context, incident lookup, and customer notification.
- `src/incident_report/synthetic_cases.py` loads synthetic test
  cases from SQLite.
- `src/incident_report/data/` contains the synthetic SQLite
  database and seed SQL.
- `scripts/build_synthetic_db.py` rebuilds the synthetic SQLite database.
- `src/incident_report/report_writer.py` writes Markdown reports.
- `src/incident_report/sample_data.py` provides the sample
  customer and service-status data used by the CLI.

from __future__ import annotations

from importlib import resources

import duckdb
import pandas as pd
from pydantic_ai import Agent, ModelRetry, RunContext

from .constants import LOCAL_DATASETS
from .deps import AnalystAgentDeps


def load_local_dataset(
    ctx: RunContext[AnalystAgentDeps],
    name: str = "shipments",
) -> str:
    """Load a local CSV dataset bundled with this example.

    Args:
        ctx: Pydantic AI agent RunContext
        name: local dataset name. Use list_local_datasets to see available datasets.
    """
    filename = LOCAL_DATASETS.get(name)
    if filename is None:
        valid_names = ", ".join(sorted(LOCAL_DATASETS))
        raise ModelRetry(
            f"{name!r} is not a local dataset. Valid local datasets are: {valid_names}"
        )

    dataset_path = resources.files("data_analytics").joinpath("data", filename)
    with resources.as_file(dataset_path) as path:
        dataframe = pd.read_csv(path)

    ref = ctx.deps.store(dataframe)
    columns = ", ".join(str(column) for column in dataframe.columns)
    return (
        f"Loaded local dataset {name!r} as `{ref}`.\n"
        f"Rows: {len(dataframe)}\n"
        f"Columns: {columns}"
    )


def list_local_datasets(ctx: RunContext[AnalystAgentDeps]) -> str:
    """List local datasets bundled with this example."""
    if ctx.deps.available_datasets:
        dataset_names = ", ".join(sorted(ctx.deps.available_datasets))
    else:
        dataset_names = ", ".join(sorted(LOCAL_DATASETS))
    return f"Available local datasets: {dataset_names}"


def run_duckdb(ctx: RunContext[AnalystAgentDeps], dataset: str, sql: str) -> str:
    """Run DuckDB SQL query on the DataFrame.

    Note that the virtual table name used in DuckDB SQL must be `dataset`.

    Args:
        ctx: Pydantic AI agent RunContext
        dataset: reference string to the DataFrame
        sql: the query to be executed using DuckDB
    """
    data = ctx.deps.get(dataset)
    result = duckdb.query_df(df=data, virtual_table_name="dataset", sql_query=sql)
    ref = ctx.deps.store(result.df())
    return f"Executed SQL, result is `{ref}`"


def display(ctx: RunContext[AnalystAgentDeps], name: str) -> str:
    """Display at most 5 rows of the dataframe."""
    dataset = ctx.deps.get(name)
    return dataset.head().to_string()  # pyright: ignore[reportUnknownMemberType]


def register_tools(agent: Agent[AnalystAgentDeps, str]) -> Agent[AnalystAgentDeps, str]:
    agent.tool(list_local_datasets)
    agent.tool(load_local_dataset)
    agent.tool(run_duckdb)
    agent.tool(display)
    return agent

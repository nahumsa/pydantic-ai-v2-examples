from __future__ import annotations

import pandas as pd
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.capabilities import Capability

from ..deps import AnalystAgentDeps


def run_abc_analysis(
    ctx: RunContext[AnalystAgentDeps],
    dataset: str,
    item_column: str = "product_id",
    quantity_column: str = "ordered_units",
    unit_value_column: str = "unit_price",
    a_threshold: float = 0.80,
    b_threshold: float = 0.95,
) -> str:
    """Run ABC analysis on a loaded DataFrame.

    Args:
        ctx: Pydantic AI agent RunContext
        dataset: reference string to a DataFrame, such as Out[1]
        item_column: item/SKU column to classify
        quantity_column: quantity or usage column
        unit_value_column: unit cost or unit revenue column
        a_threshold: cumulative value share cutoff for class A
        b_threshold: cumulative value share cutoff for class B
    """
    if not 0 < a_threshold < b_threshold < 1:
        raise ModelRetry(
            "ABC thresholds must satisfy 0 < a_threshold < b_threshold < 1."
        )

    dataframe = ctx.deps.get(dataset)
    required_columns = {item_column, quantity_column, unit_value_column}
    missing_columns = sorted(required_columns - set(dataframe.columns))
    if missing_columns:
        raise ModelRetry(
            f"{dataset} is missing columns for ABC analysis: {', '.join(missing_columns)}"
        )

    working = dataframe[[item_column, quantity_column, unit_value_column]].copy()
    working[quantity_column] = pd.to_numeric(working[quantity_column], errors="coerce")
    working[unit_value_column] = pd.to_numeric(
        working[unit_value_column], errors="coerce"
    )
    working = working.dropna(subset=[item_column, quantity_column, unit_value_column])
    if working.empty:
        raise ModelRetry("ABC analysis has no valid numeric rows after cleaning.")

    working["extended_value"] = working[quantity_column] * working[unit_value_column]
    summary = (
        working.groupby(item_column, as_index=False)
        .agg(
            total_quantity=(quantity_column, "sum"),
            total_value=("extended_value", "sum"),
        )
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )
    total_value = float(summary["total_value"].sum())
    if total_value <= 0:
        raise ModelRetry("ABC analysis requires a positive total value.")

    summary["value_share"] = summary["total_value"] / total_value
    summary["cumulative_value_share"] = summary["value_share"].cumsum()
    previous_cumulative_share = summary["cumulative_value_share"] - summary["value_share"]
    summary["abc_class"] = previous_cumulative_share.map(
        lambda share: "A" if share < a_threshold else "B" if share < b_threshold else "C"
    )

    ref = ctx.deps.store(summary)
    class_counts = summary["abc_class"].value_counts().sort_index()
    counts = ", ".join(
        f"{abc_class}: {count}" for abc_class, count in class_counts.items()
    )
    return (
        f"ABC analysis result stored as `{ref}`.\n"
        f"Items classified: {len(summary)}\n"
        f"Class counts: {counts}"
    )


def build_abc_analysis_capability() -> Capability[AnalystAgentDeps]:
    abc_analysis = Capability[AnalystAgentDeps](
        id="abc-analysis",
        instructions=(
            "Use run_abc_analysis when the user asks for ABC, Pareto, inventory "
            "value segmentation, or SKU value classification."
        ),
        description="Classifies supply-chain items into A/B/C classes by cumulative value share.",
        defer_loading=True,
    )
    abc_analysis.tool(run_abc_analysis, metadata={"capability": "abc-analysis"})
    return abc_analysis

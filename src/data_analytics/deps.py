from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from pydantic_ai import ModelRetry


@dataclass
class AnalystAgentDeps:
    available_datasets: Optional[list[str]] = None
    output: dict[str, pd.DataFrame] = field(default_factory=dict[str, pd.DataFrame])

    def store(self, value: pd.DataFrame) -> str:
        """Store output in deps and return a reference such as Out[1]."""
        ref = f"Out[{len(self.output) + 1}]"
        self.output[ref] = value
        return ref

    def get(self, ref: str) -> pd.DataFrame:
        if ref not in self.output:
            raise ModelRetry(
                f"Error: {ref} is not a valid variable reference. Check the previous messages and try again."
            )
        return self.output[ref]

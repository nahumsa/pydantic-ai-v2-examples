from __future__ import annotations

DEFAULT_PROMPT = (
    "List the local supply chain datasets, then load shipments and summarize delayed shipments by carrier."
)
DEFAULT_MODEL = "openai/gpt-oss-120b:free"
DEFAULT_REQUEST_LIMIT = 8
DEFAULT_OUTPUT_TOKEN_LIMIT = 1_200
DEFAULT_MODEL_MAX_TOKENS = 500
INSTRUCTIONS = "You are a data analyst and your job is to analyze the data according to the user request."
LOCAL_DATASETS = {
    "demand_forecast": "supply_chain_demand_forecast.csv",
    "inventory": "supply_chain_inventory.csv",
    "orders": "supply_chain_orders.csv",
    "shipments": "supply_chain_shipments.csv",
    "suppliers": "supply_chain_suppliers.csv",
}
